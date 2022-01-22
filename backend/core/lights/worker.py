"""This module contains the worker class calculating the visualizations."""

from __future__ import annotations

import math
import os
import shutil
import signal
import subprocess
from threading import Thread, Event
import time
from typing import Dict, Optional, NamedTuple, Tuple, TypedDict, cast

from django.db import connection

from django.conf import settings as conf
from core import redis
from core.tasks import app
from core.lights import controller, lights
from core.lights import leds
from core.lights.ring import Ring
from core.lights.wled import WLED
from core.lights.strip import Strip
from core.lights.screen import Screen
from core.lights.device import Device
from core.lights.programs import LedProgram, LightProgram, ScreenProgram
from core.lights.programs import Alarm, Cava, Disabled
from core.lights.led_programs import Adaptive, Fixed, Rainbow
from core.lights.exceptions import ScreenProgramStopped
from core.lights.screen_programs import Visualization, Video
from core.settings import storage
from core.settings.storage import DeviceBrightness, DeviceMonochrome, DeviceProgram
from core.util import optional

lights_lock = redis.connection.lock("lights_lock")


class Settings(TypedDict):
    """A type containing all settings affecting multiple programs."""

    ups: float
    dynamic_resolution: bool
    program_speed: float
    fixed_color: Tuple[float, float, float]
    last_fixed_color: Tuple[float, float, float]


class Utilities(NamedTuple):
    """A type containing all utility programs that can not run directly on a device."""

    disabled: Disabled
    cava: Cava
    alarm: Alarm


class Devices(NamedTuple):
    """A type containing all available devices."""

    ring: Ring
    strip: Strip
    wled: WLED
    screen: Screen


def start() -> None:
    """Initializes this module by starting the lights loop."""
    _loop.delay()
    connection.close()


class DeviceManager:
    """A class managing all visualization devices.
    This class maintains state, but only in the worker thread that updates the lights.
    This keeps the necessary variables local to the thread, avoiding db/redis queries each frame."""

    def __init__(self) -> None:

        self.loop_active: Optional[Event] = Event()

        self.devices = Devices(Ring(self), Strip(self), WLED(self), Screen(self))

        # these settings are mirrored from the database,
        # because some of them are accessed multiple times per update.
        self.settings: Settings = {
            "ups": storage.get("ups"),
            "dynamic_resolution": storage.get("dynamic_resolution"),
            "program_speed": storage.get("program_speed"),
            "fixed_color": storage.get("fixed_color"),
            "last_fixed_color": storage.get("fixed_color"),
        }

        self.utilities = Utilities(Disabled(self), Cava(self), Alarm(self))
        cava_installed = shutil.which("cava") is not None

        # a dictionary containing all led programs by their name
        led_programs: Dict[str, LedProgram] = {
            self.utilities.disabled.name: self.utilities.disabled
        }
        led_program_classes = [Fixed, Rainbow]
        if cava_installed:
            led_program_classes.append(Adaptive)
        for led_program_class in led_program_classes:
            led_program = led_program_class(self)
            led_programs[led_program.name] = led_program
        # a dictionary containing all screen programs by their name
        screen_programs: Dict[str, ScreenProgram] = {
            self.utilities.disabled.name: self.utilities.disabled
        }
        logo_loop = Video(self, "LogoLoop.mp4", loop=True)
        screen_programs[logo_loop.name] = logo_loop
        if cava_installed:
            for variant in sorted(Visualization.get_variants()):
                screen_programs[variant] = Visualization(self, variant)

        redis.put("led_programs", list(led_programs.keys()))
        redis.put("screen_programs", list(screen_programs.keys()))

        # a dictionary containing *all* programs by their name
        self.programs: Dict[str, LightProgram] = {**led_programs, **screen_programs}

        for device in self.devices:
            device.load_program()

        self.consumers_changed()

        self.listener = Thread(target=self.listen_for_changes)
        self.listener.start()

    def listen_for_changes(self) -> None:
        """Listens for changed settings on the redis channel and acts accordingly."""
        pubsub = redis.connection.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe("lights_settings_changed")
        for message in pubsub.listen():
            settings_changed = message["data"]

            if settings_changed == "stop":
                # delete the lock the main thread is checking each loop in order to stop it
                # this removes the need for an extra redis variable
                # that would need to be checked every loop
                if self.loop_active is not None:
                    self.loop_active.set()
                    self.loop_active = None
                break

            if settings_changed == "alarm_started":
                self.alarm_started()
                continue
            if settings_changed == "alarm_stopped":
                self.alarm_stopped()
                continue

            # flush the cache before accessing the database so no stale data is read
            storage.cache.clear()

            if settings_changed == "adjust_screen":
                self.devices.screen.adjust()
                # restart the screen program after a resolution change so it fits the screen again
                if storage.get("initial_resolution") != self.devices.screen.resolution:
                    # changing resolutions takes a while, wait until it was applied
                    self.restart_screen_program(sleep_time=2)
                else:
                    self.restart_screen_program()
                continue

            if settings_changed == "base":
                # base settings affecting every device were modified
                if not math.isclose(self.settings["ups"], storage.get("ups")):
                    # only update ups if they actually changed,
                    # because cava and the screen program need to be restarted
                    old_ups = self.settings["ups"]
                    self.settings["ups"] = storage.get("ups")
                    self.set_cava_framerate()
                    self.restart_screen_program(sleep_time=1 / old_ups * 5)
                self.settings["dynamic_resolution"] = storage.get("dynamic_resolution")
                self.settings["fixed_color"] = storage.get("fixed_color")
                self.settings["program_speed"] = storage.get("program_speed")
                continue

            # a device was changed
            # reload all settings for this device from the database
            # instead of communicating the exact changed setting.
            device_name = settings_changed
            device = getattr(self.devices, device_name)
            assert device_name in ["ring", "strip", "wled", "screen"]
            device.brightness = storage.get(
                cast(DeviceBrightness, f"{device_name}_brightness")
            )
            device.monochrome = storage.get(
                cast(DeviceMonochrome, f"{device_name}_monochrome")
            )
            if device_name == "wled":
                self.devices.wled.ip = storage.get("wled_ip")
                self.devices.wled.port = storage.get("wled_port")
            program = self.programs[
                storage.get(cast(DeviceProgram, f"{device_name}_program"))
            ]
            self.set_program(device, program)
        connection.close()

    def set_program(
        self, device: Device, program: LightProgram, has_lock=False
    ) -> None:
        """Changes the program of the given device to the given program."""
        # don't allow program change on disconnected devices
        if not device.initialized:
            return

        with optional(not has_lock, lights_lock):
            if device.program == program:
                # nothing to do
                return

            device.program.release()
            # see explanation in except ScreenProgramStopped why we don't always use() here
            if not (
                isinstance(
                    self.programs[storage.get("last_screen_program")], Visualization
                )
                and isinstance(
                    self.programs[storage.get("screen_program")], Visualization
                )
            ):
                program.use()

            device.program = program
            self.consumers_changed()

            if program.name == "Disabled":
                device.clear()

        # Disable the pwr led if the ring is active.
        # The pwr led ruins the clean look of a ring spectrum,
        # and an active led ring is enough of an indicator that the Pi is running.
        if device.name == "ring":
            if program.name == "Disabled":
                leds.enable_pwr_led()
            else:
                leds.disable_pwr_led()

    def consumers_changed(self) -> None:
        """Stops the loop if no led is active, starts it otherwise"""
        if self.utilities.disabled.consumers == 4:
            assert self.loop_active
            self.loop_active.clear()
            redis.put("lights_active", False)
        else:
            assert self.loop_active
            self.loop_active.set()
            redis.put("lights_active", True)

    def alarm_started(self) -> None:
        """Makes alarm the current program but doesn't update the database."""
        self.utilities.alarm.use()

        leds.disable_pwr_led()

        self.settings["last_fixed_color"] = self.settings["fixed_color"]
        for device in [self.devices.ring, self.devices.wled, self.devices.strip]:
            self.set_program(device, self.programs["Fixed"])
        # the screen program adapts with the alarm and is not changed

    def alarm_stopped(self) -> None:
        """Restores the state from before the alarm."""
        self.utilities.alarm.release()
        self.settings["fixed_color"] = self.settings["last_fixed_color"]

        leds.enable_pwr_led()

        # the database still contains the program from before the alarm. restore it.
        for device in [self.devices.ring, self.devices.wled, self.devices.strip]:
            self.set_program(
                device,
                self.programs[
                    storage.get(cast(DeviceProgram, f"{device.name}_program"))
                ],
            )

    def restart_screen_program(self, sleep_time=None, has_lock=False) -> None:
        """Restarts the current screen program. Waits sleep_time seconds in the Disabled state."""
        if self.devices.screen.program == self.utilities.disabled:
            return
        screen_program = self.devices.screen.program
        self.set_program(
            self.devices.screen, self.utilities.disabled, has_lock=has_lock
        )
        # wait until the program was computed, so it executed its shutdown
        if sleep_time:
            time.sleep(sleep_time)
        else:
            time.sleep(1 / self.settings["ups"] * 5)
        self.set_program(self.devices.screen, screen_program, has_lock=has_lock)

    def set_cava_framerate(self) -> None:
        """Update the cava.config file to contain the current framerate."""
        subprocess.call(
            [
                "sed",
                "-i",
                "-r",
                "-e",
                f"s/(^framerate\\s*=).*/\\1 {self.settings['ups']}/",
                os.path.join(conf.BASE_DIR, "config/cava.config"),
            ]
        )
        if self.utilities.cava.cava_process:
            self.utilities.cava.cava_process.send_signal(signal.SIGUSR1)

    def _set_led_colors(self) -> None:
        assert isinstance(self.devices.ring.program, LedProgram)
        assert isinstance(self.devices.strip.program, LedProgram)
        assert isinstance(self.devices.wled.program, LedProgram)
        if self.devices.ring.program.name != "Disabled":
            if self.devices.ring.monochrome:
                ring_colors = [
                    self.devices.ring.program.strip_color()
                    for _ in range(self.devices.ring.LED_COUNT)
                ]
            else:
                ring_colors = self.devices.ring.program.ring_colors()
            self.devices.ring.set_colors(ring_colors)

        if self.devices.strip.program.name != "Disabled":
            strip_color = self.devices.strip.program.strip_color()
            self.devices.strip.set_color(strip_color)

        if self.devices.wled.program.name != "Disabled":
            if self.devices.wled.monochrome:
                wled_colors = [
                    self.devices.wled.program.strip_color()
                    for _ in range(self.devices.wled.led_count)
                ]
            else:
                wled_colors = self.devices.wled.program.wled_colors()
            self.devices.wled.set_colors(wled_colors)

    def loop(self) -> None:
        """The main lights loop. When active, compute every active program and set the devices."""
        while True:
            try:
                self.loop_active.wait()  # type: ignore[union-attr]
            except AttributeError:
                # the lock was deleted by the listener thread in order to stop the main thread
                # The display must be stopped from this thread, otherwise no new one can be created
                self.devices.screen.program.stop()
                self.listener.join()
                break

            computation_start = time.time()

            with lights_lock:
                # these programs only actually do work if their respective programs are active
                self.utilities.cava.compute()
                self.utilities.alarm.compute()

                self.devices.ring.program.compute()
                if self.devices.wled.program != self.devices.ring.program:
                    self.devices.wled.program.compute()
                if self.devices.strip.program != self.devices.ring.program:
                    self.devices.strip.program.compute()

                self._set_led_colors()

                try:
                    self.devices.screen.program.compute()
                except ScreenProgramStopped:
                    # If the program changes from one Visualization program to another,
                    # the new program will set active to true immediately,
                    # but the old program will set active to false only during the next frame.
                    # This would mean that active will stay false even though rendering takes place.
                    # We prevent this by starting the new program only after the old one stopped.
                    # This happens when this exception was catched
                    # and we switched from one Visualization program to another.
                    #
                    # This exception is also thrown if the window is closed.
                    # For these cases, set the program to disabled.
                    # This means that if the windows *is* closed
                    # after switching from one Visualization program to another,
                    # the program will not be set to disabled. This is a corner case we accept.
                    # It would be fixed by introducing a variable
                    # and checking whether such a change occurred in the recent past.
                    if isinstance(
                        self.programs[storage.get("last_screen_program")], Visualization
                    ) and isinstance(
                        self.programs[storage.get("screen_program")], Visualization
                    ):
                        self.programs[storage.get("screen_program")].use()
                    else:
                        self.set_program(
                            self.devices.screen, self.utilities.disabled, has_lock=True
                        )
                        controller.persist_program_change("screen", "Disabled")
                        lights.update_state()

            computation_time = time.time() - computation_start
            try:
                time.sleep(1 / self.settings["ups"] - computation_time)
            except ValueError:
                pass


@app.task
def _loop() -> None:
    manager = DeviceManager()
    manager.loop()
    connection.close()
