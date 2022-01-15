"""This module contains the worker class calculating the visualizations."""

from __future__ import annotations

import math
import os
import shutil
import signal
import subprocess
from threading import Thread, Event
import time
from typing import Dict, TYPE_CHECKING, TypeVar

from django.db import connection

from django.conf import settings as conf
from core import redis
from core.celery import app
from core.lights import controller, lights
from core.lights import leds
from core.lights.device import Device
from core.lights.programs import LedProgram, LightProgram, ScreenProgram
from core.lights.programs import Alarm, Cava, Disabled
from core.lights.led_programs import Adaptive, Fixed, Rainbow
from core.lights.exceptions import ScreenProgramStopped
from core.lights.screen_programs import Visualization, Video
from core.settings import storage
from core.util import optional

if TYPE_CHECKING:
    from core.lights.ring import Ring
    from core.lights.wled import WLED
    from core.lights.strip import Strip
    from core.lights.screen import Screen

    T = TypeVar("T", Ring, WLED, Strip)  # pylint: disable=invalid-name

lights_lock = redis.lock("lights_lock")


def start() -> None:
    _loop.delay()
    connection.close()


class DeviceManager:
    """A class managing all visualization devices.
    This class maintains state, but only in the worker thread that updates the lights.
    This keeps the necessary variables local to the thread, avoiding db/redis queries each frame."""

    def __init__(self) -> None:
        from core.lights.ring import Ring
        from core.lights.wled import WLED
        from core.lights.strip import Strip
        from core.lights.screen import Screen

        self.ups = storage.get("ups")
        self.seconds_per_frame = 1 / self.ups

        self.loop_active = Event()

        self.disabled_program = Disabled(self)

        self.ring = Ring(self)
        self.wled = WLED(self)
        self.strip = Strip(self)
        self.screen = Screen(self)

        self.dynamic_resolution = storage.get("dynamic_resolution")

        self.cava_program = Cava(self)
        cava_installed = shutil.which("cava") is not None
        self.alarm_program = Alarm(self)

        # a dictionary containing all devices by their name
        self.all_devices: Dict[str, Device] = {
            device.name: device
            for device in [self.ring, self.wled, self.strip, self.screen]
        }
        # a dictionary containing all led programs by their name
        self.led_programs: Dict[str, LedProgram] = {
            self.disabled_program.name: self.disabled_program
        }
        led_program_classes = [Fixed, Rainbow]
        if cava_installed:
            led_program_classes.append(Adaptive)
        for led_program_class in led_program_classes:
            led_program = led_program_class(self)
            self.led_programs[led_program.name] = led_program
        # a dictionary containing all screen programs by their name
        self.screen_programs: Dict[str, ScreenProgram] = {
            self.disabled_program.name: self.disabled_program
        }
        logo_loop = Video(self, "LogoLoop.mp4", loop=True)
        self.screen_programs[logo_loop.name] = logo_loop
        if cava_installed:
            for variant in sorted(Visualization.get_variants()):
                self.screen_programs[variant] = Visualization(self, variant)

        redis.set("led_programs", list(self.led_programs.keys()))
        redis.set("screen_programs", list(self.screen_programs.keys()))

        # a dictionary containing *all* programs by their name
        self.all_programs: Dict[str, LightProgram] = {
            **self.led_programs,
            **self.screen_programs,
        }
        self.program_speed = storage.get("program_speed")
        self.fixed_color = storage.get("fixed_color")
        self.last_fixed_color = self.fixed_color

        for device in [self.ring, self.wled, self.strip, self.screen]:
            device.load_program()

        self.consumers_changed()

        self.listener = Thread(target=self.listen_for_changes)
        self.listener.start()

    def listen_for_changes(self) -> None:
        p = redis.pubsub(ignore_subscribe_messages=True)
        p.subscribe("lights_settings_changed")
        for message in p.listen():
            settings_changed = message["data"]

            if settings_changed == "stop":
                # delete the lock the main thread is checking each loop in order to stop it
                # this removes the need for an extra redis variable
                # that would need to be checked every loop
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
                self.screen.adjust()
                # restart the screen program after a resolution change so it fits the screen again
                if storage.get("initial_resolution") != self.screen.resolution:
                    # changing resolutions takes a while, wait until it was applied
                    self.restart_screen_program(sleep_time=2)
                else:
                    self.restart_screen_program()
                continue

            if settings_changed == "base":
                # base settings affecting every device were modified
                if not math.isclose(self.ups, storage.get("ups")):
                    # only update ups if they actually changed,
                    # because cava and the screen program need to be restarted
                    old_ups = self.ups
                    self.ups = storage.get("ups")
                    self.set_cava_framerate()
                    self.restart_screen_program(sleep_time=1 / old_ups * 5)
                self.dynamic_resolution = storage.get("dynamic_resolution")
                self.fixed_color = storage.get("fixed_color")
                self.program_speed = storage.get("program_speed")
                continue

            # a device was changed
            # reload all settings for this device from the database
            # instead of communicating the exact changed setting.
            device_name = settings_changed
            device = self.all_devices[device_name]
            device.brightness = storage.get(f"{device_name}_brightness")
            device.monochrome = storage.get(f"{device_name}_monochrome")
            if device_name == "wled":
                self.wled.ip = storage.get("wled_ip")
                self.wled.port = storage.get("wled_port")
            program = self.all_programs[storage.get(f"{device_name}_program")]
            self.set_program(device, program)
        connection.close()

    def set_program(
        self, device: Device, program: LightProgram, has_lock=False
    ) -> None:
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
                    self.all_programs[storage.get("last_screen_program")], Visualization
                )
                and isinstance(
                    self.all_programs[storage.get("screen_program")], Visualization
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
        if self.disabled_program.consumers == 4:
            self.loop_active.clear()
            redis.set("lights_active", False)
        else:
            self.loop_active.set()
            redis.set("lights_active", True)

    def alarm_started(self) -> None:
        """Makes alarm the current program but doesn't update the database."""
        self.alarm_program.use()

        leds.disable_pwr_led()

        self.last_fixed_color = self.fixed_color
        for device in [self.ring, self.wled, self.strip]:
            self.set_program(device, self.led_programs["Fixed"])
        # the screen program adapts with the alarm and is not changed

    def alarm_stopped(self) -> None:
        """Restores the state from before the alarm."""
        self.alarm_program.release()
        self.fixed_color = self.last_fixed_color

        leds.enable_pwr_led()

        # the database still contains the program from before the alarm. restore it.
        for device in [self.ring, self.wled, self.strip]:
            self.set_program(
                device, self.led_programs[storage.get(f"{device.name}_program")]
            )

    def restart_screen_program(self, sleep_time=None, has_lock=False) -> None:
        if self.screen.program == self.disabled_program:
            return
        screen_program = self.screen.program
        self.set_program(self.screen, self.disabled_program, has_lock=has_lock)
        # wait until the program was computed, so it executed its shutdown
        if sleep_time:
            time.sleep(sleep_time)
        else:
            time.sleep(1 / self.ups * 5)
        self.set_program(self.screen, screen_program, has_lock=has_lock)

    def set_cava_framerate(self):
        subprocess.call(
            [
                "sed",
                "-i",
                "-r",
                "-e",
                f"s/(^framerate\\s*=).*/\\1 {self.ups}/",
                os.path.join(conf.BASE_DIR, "config/cava.config"),
            ]
        )
        if self.cava_program.cava_process:
            self.cava_program.cava_process.send_signal(signal.SIGUSR1)

    def loop(self):
        while True:
            try:
                self.loop_active.wait()
            except AttributeError:
                # the lock was deleted by the listener thread in order to stop the main thread
                # The display must be stopped from this thread, otherwise no new one can be created
                self.screen.program.stop()
                self.listener.join()
                break

            computation_start = time.time()

            with lights_lock:
                # these programs only actually do work if their respective programs are active
                self.cava_program.compute()
                self.alarm_program.compute()

                self.ring.program.compute()
                if self.wled.program != self.ring.program:
                    self.wled.program.compute()
                if self.strip.program != self.ring.program:
                    self.strip.program.compute()

                if self.ring.program.name != "Disabled":
                    if self.ring.monochrome:
                        ring_colors = [
                            self.ring.program.strip_color()
                            for _ in range(self.ring.LED_COUNT)
                        ]
                    else:
                        ring_colors = self.ring.program.ring_colors()
                    self.ring.set_colors(ring_colors)

                if self.strip.program.name != "Disabled":
                    strip_color = self.strip.program.strip_color()
                    self.strip.set_color(strip_color)

                if self.wled.program.name != "Disabled":
                    if self.wled.monochrome:
                        wled_colors = [
                            self.wled.program.strip_color()
                            for _ in range(self.wled.led_count)
                        ]
                    else:
                        wled_colors = self.wled.program.wled_colors()
                    self.wled.set_colors(wled_colors)

                try:
                    self.screen.program.compute()
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
                        self.all_programs[storage.get("last_screen_program")],
                        Visualization,
                    ) and isinstance(
                        self.all_programs[storage.get("screen_program")], Visualization
                    ):
                        self.all_programs[storage.get("screen_program")].use()
                    else:
                        self.set_program(
                            self.screen, self.disabled_program, has_lock=True
                        )
                        controller.persist_program_change("screen", "Disabled")
                        lights.update_state()

            computation_time = time.time() - computation_start
            try:
                time.sleep(self.seconds_per_frame - computation_time)
            except ValueError:
                pass


@app.task
def _loop() -> None:
    manager = DeviceManager()
    manager.loop()
    connection.close()
