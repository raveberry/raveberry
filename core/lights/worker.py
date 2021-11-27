"""This module contains the worker class calculating the visualizations."""

from __future__ import annotations

from threading import Thread, Event
import time
from typing import Dict, TYPE_CHECKING, TypeVar

from django.db import connection

from core import redis
from core.celery import app
from core.lights import leds
from core.lights.circle.circle import Circle
from core.lights.device import Device
from core.lights.programs import Adaptive, LedProgram, ScreenProgram, VizProgram
from core.lights.programs import Alarm
from core.lights.programs import Cava
from core.lights.programs import Disabled
from core.lights.programs import Fixed
from core.lights.programs import Rainbow
from core.lights.exceptions import RenderingStoppedException
from core.settings import storage


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

        self.ups = 30
        self.seconds_per_frame = 1 / self.ups

        self.loop_active = Event()

        self.disabled_program = Disabled(self)

        self.ring = Ring(self)
        self.wled = WLED(self)
        self.strip = Strip(self)
        self.screen = Screen(self)

        self.cava_program = Cava(self)
        self.alarm_program = Alarm(self)

        # a dictionary containing all devices by their name
        self.all_devices: Dict[str, Device] = {
            device.name: device
            for device in [self.ring, self.wled, self.strip, self.screen]
        }
        # a dictionary containing all led programs by their name
        self.led_programs: Dict[str, LedProgram] = {"Disabled": self.disabled_program}
        for led_program_class in [Fixed, Rainbow, Adaptive]:
            led_instance = led_program_class(self)
            self.led_programs[led_instance.name] = led_instance
        # a dictionary containing all screen programs by their name
        self.screen_programs: Dict[str, ScreenProgram] = {
            "Disabled": self.disabled_program
        }
        for screen_program_class in [Circle]:
            screen_instance = screen_program_class(self)
            self.screen_programs[screen_instance.name] = screen_instance
        # a dictionary containing *all* programs by their name
        self.all_programs: Dict[str, VizProgram] = {
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

            if settings_changed == "base":
                # base settings affecting every device were modified
                self.fixed_color = storage.get("fixed_color")
                self.program_speed = storage.get("program_speed")
                continue

            if settings_changed == "adjust_screen":
                self.screen.adjust()
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

    def set_program(self, device: Device, program: VizProgram) -> None:
        # don't allow program change on disconnected devices
        if not device.initialized:
            return

        with lights_lock:
            if device.program == program:
                # nothing to do
                return

            device.program.release()
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

    def loop(self):
        iteration_count = 0
        adaptive_quality_window = self.ups * 10
        time_sum = 0.0
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

                if self.screen.program.name != "Disabled":
                    try:
                        self.screen.program.draw()
                    except RenderingStoppedException:
                        self.set_program(self.screen, self.disabled_program)

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

                if self.wled.program.name != "Disabled":
                    if self.wled.monochrome:
                        wled_colors = [
                            self.wled.program.strip_color()
                            for _ in range(self.wled.led_count)
                        ]
                    else:
                        wled_colors = self.wled.program.wled_colors()
                    self.wled.set_colors(wled_colors)

                if self.strip.program.name != "Disabled":
                    strip_color = self.strip.program.strip_color()
                    self.strip.set_color(strip_color)

            computation_time = time.time() - computation_start

            if self.screen.program.name != "Disabled":
                time_sum += computation_time
                iteration_count += 1
                if (
                    iteration_count >= adaptive_quality_window
                    or time_sum
                    >= 1.5 * adaptive_quality_window * self.seconds_per_frame
                ):
                    average_computation_time = time_sum / adaptive_quality_window
                    iteration_count = 0
                    time_sum = 0.0

                    # print(f"avg: {average_computation_time/seconds_per_frame}")
                    if average_computation_time > 0.9 * self.seconds_per_frame:
                        # if the loop takes too long and a screen program is active,
                        # it can be reduced in resolution to save time
                        self.screen.program.decrease_resolution()
                    elif average_computation_time < 0.6 * self.seconds_per_frame:
                        # if the loop has time to spare and a screen program is active,
                        # we can increase its quality
                        self.screen.program.increase_resolution()

            # print(f'computation took {computation_time:.5f}s')
            try:
                time.sleep(self.seconds_per_frame - computation_time)
            except ValueError:
                pass


@app.task
def _loop() -> None:
    manager = DeviceManager()
    manager.loop()
    connection.close()
