"""This module handles the visualizations for leds and screen."""

from __future__ import annotations

import logging
import threading
import time
from ast import literal_eval as make_tuple
from functools import wraps
from typing import Callable, Dict, Any, Optional, TYPE_CHECKING, TypeVar, List

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import URLPattern

from core.lights.circle.circle import Circle
from core.lights.programs import Adaptive, LedProgram, ScreenProgram, VizProgram
from core.lights.programs import Alarm
from core.lights.programs import Cava
from core.lights.programs import Disabled
from core.lights.programs import Fixed
from core.lights.programs import Rainbow
from core.lights.screen import RenderingStoppedException
from core.models import Setting
from core.settings.settings import Settings
from core.state_handler import Stateful
from core.util import background_thread

if TYPE_CHECKING:
    from core.base import Base
    from core.lights.ring import Ring
    from core.lights.wled import WLED
    from core.lights.strip import Strip
    from core.lights.screen import Screen

    T = TypeVar("T", Ring, WLED, Strip)  # pylint: disable=invalid-name


class Lights(Stateful):
    """This class manages the updating of visualizations."""

    UPS = 30

    @staticmethod
    def option(
        func: Callable[[T, WSGIRequest], Optional[HttpResponse]]
    ) -> Callable[[T, WSGIRequest], HttpResponse]:
        """A decorator that makes sure that all changes to the lights are synchronized."""

        def _decorator(self: T, request: WSGIRequest) -> HttpResponse:
            # only privileged users can change options during voting system
            if (
                self.lights.base.settings.basic.voting_system
                and not self.lights.base.user_manager.has_controls(request.user)
            ):
                return HttpResponseForbidden()
            # don't allow option changes during alarm
            if self.lights.base.musiq.playback.alarm_playing.is_set():
                return HttpResponseForbidden()
            with self.lights.option_lock:
                try:
                    response = func(self, request)
                    if response is not None:
                        return response
                except (ValueError, IndexError) as e:
                    logging.exception("exception during lights option: %s", e)
                    return HttpResponseBadRequest()
                self.lights.update_state()
            return HttpResponse()

        return wraps(func)(_decorator)

    def __init__(self, base: "Base") -> None:
        from core.lights.controller import Controller
        from core.lights.ring import Ring
        from core.lights.wled import WLED
        from core.lights.strip import Strip
        from core.lights.screen import Screen

        self.base = base
        self.urlpatterns: List[URLPattern] = []

        self.seconds_per_frame = 1 / self.UPS

        self.controller = Controller(self)

        # if the led loop is running
        self.loop_active = threading.Event()

        self.disabled_program = Disabled(self)

        self.ring = Ring(self)
        self.wled = WLED(self)
        self.strip = Strip(self)
        self.screen = Screen(self)

        self.cava_program = Cava(self)
        self.alarm_program = Alarm(self)
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

        # this lock ensures that only one thread changes led options
        self.option_lock = threading.Lock()
        self.program_speed = float(Settings.get_setting("program_speed", "0.5"))
        self.fixed_color = make_tuple(Settings.get_setting("fixed_color", "(0, 0, 0)"))
        self.last_fixed_color = self.fixed_color

        for device in [self.ring, self.wled, self.strip, self.screen]:
            device.load_program()

        self.consumers_changed()

    def start(self) -> None:
        self._loop()

    @background_thread
    def _loop(self) -> None:
        iteration_count = 0
        adaptive_quality_window = self.UPS * 10
        time_sum = 0.0
        while True:
            self.loop_active.wait()

            with self.option_lock:
                computation_start = time.time()

                # these programs only actually do work if their respective programs are active
                self.cava_program.compute()
                self.alarm_program.compute()

                if self.screen.program.name != "Disabled":
                    try:
                        self.screen.program.draw()
                    except RenderingStoppedException:
                        self.controller.set_program(self.screen, self.disabled_program)

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

                    # print(f"avg: {average_computation_time/self.seconds_per_frame}")
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

    def consumers_changed(self) -> None:
        """Stops the loop if no led is active, starts it otherwise"""
        if self.disabled_program.consumers == 4:
            self.loop_active.clear()
        else:
            self.loop_active.set()

    def alarm_started(self) -> None:
        """Makes alarm the current program but doesn't update the database."""
        with self.option_lock:
            self.alarm_program.use()
            self.last_fixed_color = self.fixed_color
            for device in [self.ring, self.wled, self.strip]:
                self.controller.set_program(
                    device, self.led_programs["Fixed"], transient=True
                )
            # the screen program adapts with the alarm and is not changed

    def alarm_stopped(self) -> None:
        """Restores the state from before the alarm."""
        with self.option_lock:
            self.alarm_program.release()
            self.fixed_color = self.last_fixed_color

            # read last programs from database, which is still in the state before the alarm
            for device in [self.ring, self.wled, self.strip]:
                self.controller.set_program(device, device.last_program, transient=True)
                last_program_name = Setting.objects.get(
                    key=f"last_{device.name}_program"
                ).value
                device.last_program = self.led_programs[last_program_name]

    def state_dict(self) -> Dict[str, Any]:
        state_dict = self.base.state_dict()

        lights_state = {}
        lights_state["ringConnected"] = self.ring.initialized
        lights_state["ringProgram"] = self.ring.program.name
        lights_state["ringBrightness"] = self.ring.brightness
        lights_state["ringMonochrome"] = self.ring.monochrome
        lights_state["wledLedCount"] = self.wled.led_count
        lights_state["wledIp"] = self.wled.ip
        lights_state["wledPort"] = self.wled.port
        lights_state["wledConnected"] = self.wled.initialized
        lights_state["wledProgram"] = self.wled.program.name
        lights_state["wledBrightness"] = self.wled.brightness
        lights_state["wledMonochrome"] = self.wled.monochrome
        lights_state["stripConnected"] = self.strip.initialized
        lights_state["stripProgram"] = self.strip.program.name
        lights_state["stripBrightness"] = self.strip.brightness
        lights_state["screenConnected"] = self.screen.initialized
        lights_state["screenProgram"] = self.screen.program.name
        lights_state["programSpeed"] = self.program_speed
        lights_state["fixedColor"] = "#{:02x}{:02x}{:02x}".format(
            *(int(val * 255) for val in self.fixed_color)
        )

        state_dict["lights"] = lights_state
        return state_dict

    def index(self, request: WSGIRequest) -> HttpResponse:
        """Renders the /lights page. During voting, only privileged users can access this."""
        if (
            self.base.settings.basic.voting_system
            and not self.base.user_manager.has_controls(request.user)
        ):
            return redirect("login")
        context = self.base.context(request)
        context["urls"] = self.urlpatterns
        # programs that have a strip_color or ring_color function are color programs
        # programs that have a draw function are screen programs
        context["color_program_names"] = [
            program.name for program in self.led_programs.values()
        ]
        context["screen_program_names"] = [
            program.name for program in self.screen_programs.values()
        ]
        return render(request, "lights.html", context)
