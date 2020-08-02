"""This module handles all controls that influence visualization in general."""

from __future__ import annotations

import socket
from typing import (
    TYPE_CHECKING,
    cast,
    Tuple,
)

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponseBadRequest, HttpResponse

from core.lights.device import Device
from core.lights.lights import Lights
from core.lights.programs import VizProgram
from core.models import Setting

if TYPE_CHECKING:
    pass


class Controller:
    """This class provides endpoints for all light controls."""

    SEEK_DISTANCE = 10 * 1000

    def __init__(self, lights: "Lights") -> None:
        self.lights = lights

    def set_program(
        self, device: Device, program: VizProgram, transient: bool = False
    ) -> None:
        # don't allow program change on disconnected devices
        if not device.initialized:
            return

        device.program.release()
        program.use()

        device.last_program = device.program
        device.program = program
        if not transient:
            Setting.objects.filter(key=f"last_{device.name}_program").update(
                value=device.last_program.name
            )
            Setting.objects.filter(key=f"{device.name}_program").update(
                value=device.program.name
            )
        self.lights.consumers_changed()

        if program.name == "Disabled":
            device.clear()

    @Lights.option
    def set_lights_shortcut(self, request: WSGIRequest) -> None:
        """Stores the current lights state and restores the previous one."""
        should_enable = request.POST.get("value") == "true"
        is_enabled = (
            self.lights.ring.program.name != "Disabled"
            or self.lights.wled.program.name != "Disabled"
            or self.lights.strip.program.name != "Disabled"
        )
        if should_enable == is_enabled:
            return
        if should_enable:
            self.set_program(self.lights.ring, self.lights.ring.last_program)
            self.set_program(self.lights.wled, self.lights.wled.last_program)
            self.set_program(self.lights.strip, self.lights.strip.last_program)
        else:
            self.set_program(self.lights.ring, self.lights.disabled_program)
            self.set_program(self.lights.wled, self.lights.disabled_program)
            self.set_program(self.lights.strip, self.lights.disabled_program)

    @Lights.option
    def set_program_speed(self, request: WSGIRequest) -> None:
        """Updates the global speed of programs supporting it."""
        value = float(request.POST.get("value"))  # type: ignore
        self.lights.program_speed = value

    @Lights.option
    def set_fixed_color(self, request: WSGIRequest) -> None:
        """Updates the static color used for some programs."""
        hex_col = request.POST.get("value").lstrip("#")  # type: ignore
        # raises IndexError on wrong input, caught in option decorator
        color = tuple(int(hex_col[i : i + 2], 16) / 255 for i in (0, 2, 4))
        # https://github.com/python/mypy/issues/5068
        color = cast(Tuple[float, float, float], color)
        self.lights.fixed_color = color

    def _handle_program_request(self, device: Device, request: WSGIRequest) -> None:
        program_name = request.POST.get("program")
        if not program_name:
            return
        program = self.lights.all_programs[program_name]
        if program == device.program:
            # the program doesn't change, return immediately
            return
        self.set_program(device, program)

    def _handle_brightness_request(self, device: Device, request: WSGIRequest) -> None:
        # raises ValueError on wrong input, caught in option decorator
        value = float(request.POST.get("value"))  # type: ignore
        device.brightness = value

    def _handle_monochrome_request(self, device: Device, request: WSGIRequest) -> None:
        # raises ValueError on wrong input, caught in option decorator
        enabled = request.POST.get("value") == "true"  # type: ignore
        device.monochrome = enabled

    @Lights.option
    def set_ring_program(self, request: WSGIRequest) -> None:
        """Updates the ring program."""
        self._handle_program_request(self.lights.ring, request)

    @Lights.option
    def set_ring_brightness(self, request: WSGIRequest) -> None:
        """Updates the ring brightness."""
        self._handle_brightness_request(self.lights.ring, request)

    @Lights.option
    def set_ring_monochrome(self, request: WSGIRequest) -> None:
        """Sets whether the ring should be in one color only."""
        self._handle_monochrome_request(self.lights.ring, request)

    @Lights.option
    def set_wled_led_count(self, request: WSGIRequest) -> None:
        """Updates the wled led_count."""
        value = int(request.POST.get("value"))  # type: ignore
        if not (2 <= value <= 490):
            return
        Setting.objects.filter(key="wled_led_count").update(value=value)
        self.lights.wled.led_count = value

    @Lights.option
    def set_wled_ip(self, request: WSGIRequest) -> None:
        """Updates the wled ip."""
        value = request.POST.get("value")  # type: ignoretry:
        try:
            socket.inet_aton(value)
        except socket.error:
            return
        Setting.objects.filter(key="wled_ip").update(value=value)
        self.lights.wled.ip = value

    @Lights.option
    def set_wled_port(self, request: WSGIRequest) -> None:
        """Updates the wled port."""
        value = int(request.POST.get("value"))  # type: ignore
        if not (1024 <= value <= 65535):
            return
        Setting.objects.filter(key="wled_port").update(value=value)
        self.lights.wled.port = value

    @Lights.option
    def set_wled_program(self, request: WSGIRequest) -> None:
        """Updates the wled program."""
        self._handle_program_request(self.lights.wled, request)

    @Lights.option
    def set_wled_brightness(self, request: WSGIRequest) -> None:
        """Updates the wled brightness."""
        self._handle_brightness_request(self.lights.wled, request)

    @Lights.option
    def set_wled_monochrome(self, request: WSGIRequest) -> None:
        """Sets whether the wled should be in one color only."""
        self._handle_monochrome_request(self.lights.wled, request)

    @Lights.option
    def set_strip_program(self, request: WSGIRequest) -> None:
        """Updates the strip program."""
        self._handle_program_request(self.lights.strip, request)

    @Lights.option
    def set_strip_brightness(self, request: WSGIRequest) -> None:
        """Updates the strip brightness."""
        self._handle_brightness_request(self.lights.strip, request)

    @Lights.option
    def set_screen_program(self, request: WSGIRequest) -> None:
        """Updates the screen program."""
        self._handle_program_request(self.lights.screen, request)

    @Lights.option
    def adjust_screen(self, _request: WSGIRequest) -> HttpResponse:
        """Adjusts the resolution of the screen."""
        if self.lights.screen.program.name != "Disabled":
            return HttpResponseBadRequest(
                "Disable the screen program before readjusting"
            )
        self.lights.screen.adjust()
        return HttpResponse()
