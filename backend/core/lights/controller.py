"""This module handles all controls that influence visualization in general."""

from __future__ import annotations

import socket
from functools import wraps
from typing import cast, Tuple, Callable

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponseBadRequest, HttpResponse, HttpResponseForbidden

from core import user_manager, redis
from core.lights import lights, worker
from core.settings import storage


def control(func: Callable) -> Callable:
    """A decorator for functions that control the lights.
    Every control changes the views state and returns an empty response.
    Mod privileges are required to control the lights."""

    def _decorator(request: WSGIRequest) -> HttpResponse:
        if not user_manager.has_controls(request.user):
            return HttpResponseForbidden()

        response = func(request)
        lights.update_state()
        if response is not None:
            return response
        return HttpResponse()

    return wraps(func)(_decorator)


def _notify_settings_changed(settings: str) -> None:
    # notifies the worker thread that the given settings (eg <device> or "base") changed
    redis.publish(f"lights_settings_changed", settings)


def alarm_started() -> None:
    """Notifies the lights worker that the alarm was started."""
    _notify_settings_changed("alarm_started")


def alarm_stopped() -> None:
    """Notifies the lights worker that the alarm was stopped."""
    _notify_settings_changed("alarm_stopped")


def set_program(device: str, program: str) -> None:
    """Updates the given device to the given program."""
    current_program = storage.get(f"{device}_program")
    storage.set(f"last_{device}_program", current_program)
    storage.set(f"{device}_program", program)
    _notify_settings_changed(device)


@control
def set_lights_shortcut(request: WSGIRequest) -> None:
    """Stores the current lights state and restores the previous one."""
    should_enable = request.POST.get("value") == "true"
    is_enabled = (
        storage.get("ring_program") != "Disabled"
        or storage.get("wled_program") != "Disabled"
        or storage.get("strip_program") != "Disabled"
    )
    if should_enable == is_enabled:
        return
    if should_enable:
        for device in ["ring", "wled", "strip"]:
            set_program(device, storage.get(f"last_{device}_program"))
    else:
        for device in ["ring", "wled", "strip"]:
            set_program(device, "Disabled")


@control
def set_program_speed(request: WSGIRequest) -> None:
    """Updates the global speed of programs supporting it."""
    value = float(request.POST.get("value"))  # type: ignore
    storage.set("program_speed", value)
    _notify_settings_changed("base")


@control
def set_fixed_color(request: WSGIRequest) -> None:
    """Updates the static color used for some programs."""
    hex_col = request.POST.get("value").lstrip("#")  # type: ignore
    # raises IndexError on wrong input, caught in option decorator
    color = tuple(int(hex_col[i : i + 2], 16) / 255 for i in (0, 2, 4))
    # https://github.com/python/mypy/issues/5068
    color = cast(Tuple[float, float, float], color)
    storage.set("fixed_color", str(color))
    _notify_settings_changed("base")


def _handle_program_request(device: str, request: WSGIRequest) -> None:
    program = request.POST.get("value")
    if not program:
        return
    if program == storage.get(f"{device}_program"):
        # the program doesn't change, return immediately
        return
    set_program(device, program)


def _handle_brightness_request(device: str, request: WSGIRequest) -> None:
    # raises ValueError on wrong input, caught in option decorator
    value = float(request.POST.get("value"))  # type: ignore
    storage.set(f"{device}_brightness", value)
    _notify_settings_changed(device)


def _handle_monochrome_request(device: str, request: WSGIRequest) -> None:
    # raises ValueError on wrong input, caught in option decorator
    enabled = request.POST.get("value") == "true"  # type: ignore
    storage.set(f"{device}_monochrome", enabled)
    _notify_settings_changed(device)


@control
def set_ring_program(request: WSGIRequest) -> None:
    """Updates the ring program."""
    _handle_program_request("ring", request)


@control
def set_ring_brightness(request: WSGIRequest) -> None:
    """Updates the ring brightness."""
    _handle_brightness_request("ring", request)


@control
def set_ring_monochrome(request: WSGIRequest) -> None:
    """Sets whether the ring should be in one color only."""
    _handle_monochrome_request("ring", request)


@control
def set_wled_led_count(request: WSGIRequest) -> None:
    """Updates the wled led_count."""
    value = int(request.POST.get("value"))  # type: ignore
    if not (2 <= value <= 490):
        return
    storage.set("wled_led_count", value)
    _notify_settings_changed("wled")


@control
def set_wled_ip(request: WSGIRequest) -> None:
    """Updates the wled ip."""
    value = request.POST.get("value")  # type: ignore
    try:
        socket.inet_aton(value)
    except socket.error:
        return
    storage.set("wled_ip", value)
    _notify_settings_changed("wled")


@control
def set_wled_port(request: WSGIRequest) -> None:
    """Updates the wled port."""
    value = int(request.POST.get("value"))  # type: ignore
    if not (1024 <= value <= 65535):
        return
    storage.set("wled_port", value)
    _notify_settings_changed("wled")


@control
def set_wled_program(request: WSGIRequest) -> None:
    """Updates the wled program."""
    _handle_program_request("wled", request)


@control
def set_wled_brightness(request: WSGIRequest) -> None:
    """Updates the wled brightness."""
    _handle_brightness_request("wled", request)


@control
def set_wled_monochrome(request: WSGIRequest) -> None:
    """Sets whether the wled should be in one color only."""
    _handle_monochrome_request("wled", request)


@control
def set_strip_program(request: WSGIRequest) -> None:
    """Updates the strip program."""
    _handle_program_request("strip", request)


@control
def set_strip_brightness(request: WSGIRequest) -> None:
    """Updates the strip brightness."""
    _handle_brightness_request("strip", request)


@control
def set_screen_program(request: WSGIRequest) -> None:
    """Updates the screen program."""
    _handle_program_request("screen", request)


@control
def adjust_screen(_request: WSGIRequest) -> HttpResponse:
    """Adjusts the resolution of the screen."""
    if storage.get("screen_program") != "Disabled":
        return HttpResponseBadRequest("Disable the screen program before readjusting")
    # _notify_settings_changed("adjust_screen")
    # After disabling the screen program, it cannot be started again
    # (pi3d only shows the black background)
    # We restart the lights worker so the library is reloaded,
    # allowing the screen program to be shown again.
    # During initialization, the screen will adjust itself.
    redis.publish("lights_settings_changed", "stop")
    worker.start()

    return HttpResponse()
