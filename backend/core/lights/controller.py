"""This module handles all controls that influence visualization in general."""

from __future__ import annotations

import socket
from functools import wraps
from typing import cast, Tuple, Callable

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest

from core import user_manager, redis
from core.lights import lights
from core.settings import storage
from core.settings.storage import DeviceBrightness, DeviceMonochrome, DeviceProgram
from core.util import extract_value, strtobool


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
    redis.connection.publish("lights_settings_changed", settings)


def alarm_started() -> None:
    """Notifies the lights worker that the alarm was started."""
    _notify_settings_changed("alarm_started")


def alarm_stopped() -> None:
    """Notifies the lights worker that the alarm was stopped."""
    _notify_settings_changed("alarm_stopped")


def persist_program_change(device, program) -> None:
    """Persist the program in the database."""
    assert device in ["ring", "strip", "wled", "screen"]
    current_program = storage.get(cast(DeviceProgram, f"{device}_program"))
    storage.put(cast(DeviceProgram, f"last_{device}_program"), current_program)
    storage.put(cast(DeviceProgram, f"{device}_program"), program)


def set_program(device: str, program: str) -> None:
    """Updates the given device to the given program."""
    persist_program_change(device, program)
    _notify_settings_changed(device)


@control
def set_lights_shortcut(request: WSGIRequest) -> HttpResponse:
    """Stores the current lights state and restores the previous one."""
    value, response = extract_value(request.POST)
    should_enable = strtobool(value)
    is_enabled = (
        storage.get("ring_program") != "Disabled"
        or storage.get("wled_program") != "Disabled"
        or storage.get("strip_program") != "Disabled"
    )
    if should_enable == is_enabled:
        return HttpResponse()
    if should_enable:
        for device in ["ring", "wled", "strip"]:
            set_program(
                device, storage.get(cast(DeviceProgram, f"last_{device}_program"))
            )
    else:
        for device in ["ring", "wled", "strip"]:
            set_program(device, "Disabled")
    return response


@control
def set_ups(request: WSGIRequest) -> HttpResponse:
    """Updates the global speed of programs supporting it."""
    value, response = extract_value(request.POST)
    storage.put("ups", float(value))
    _notify_settings_changed("base")
    return response


@control
def set_program_speed(request: WSGIRequest) -> HttpResponse:
    """Updates the global speed of programs supporting it."""
    value, response = extract_value(request.POST)
    storage.put("program_speed", float(value))
    _notify_settings_changed("base")
    return response


@control
def set_fixed_color(request: WSGIRequest) -> HttpResponse:
    """Updates the static color used for some programs."""
    hex_col, response = extract_value(request.POST)
    hex_col = hex_col.lstrip("#")
    try:
        color = tuple(int(hex_col[i : i + 2], 16) / 255 for i in (0, 2, 4))
    except IndexError:
        return HttpResponseBadRequest("color needs to be in #rrggbb format")
    # https://github.com/python/mypy/issues/5068
    color = cast(Tuple[float, float, float], color)
    storage.put("fixed_color", color)
    _notify_settings_changed("base")
    return response


def _handle_program_request(device: str, request: WSGIRequest) -> HttpResponse:
    program, response = extract_value(request.POST)
    assert device in ["ring", "strip", "wled", "screen"]
    if program == storage.get(cast(DeviceProgram, f"{device}_program")):
        # the program doesn't change, return immediately
        return HttpResponse()
    set_program(device, program)
    return response


def _handle_brightness_request(device: str, request: WSGIRequest) -> HttpResponse:
    value, response = extract_value(request.POST)
    assert device in ["ring", "strip", "wled", "screen"]
    storage.put(cast(DeviceBrightness, f"{device}_brightness"), float(value))
    _notify_settings_changed(device)
    return response


def _handle_monochrome_request(device: str, request: WSGIRequest) -> HttpResponse:
    value, response = extract_value(request.POST)
    assert device in ["ring", "strip", "wled", "screen"]
    storage.put(cast(DeviceMonochrome, f"{device}_monochrome"), strtobool(value))
    _notify_settings_changed(device)
    return response


@control
def set_ring_program(request: WSGIRequest) -> HttpResponse:
    """Updates the ring program."""
    return _handle_program_request("ring", request)


@control
def set_ring_brightness(request: WSGIRequest) -> HttpResponse:
    """Updates the ring brightness."""
    return _handle_brightness_request("ring", request)


@control
def set_ring_monochrome(request: WSGIRequest) -> HttpResponse:
    """Sets whether the ring should be in one color only."""
    return _handle_monochrome_request("ring", request)


@control
def set_wled_led_count(request: WSGIRequest) -> HttpResponse:
    """Updates the wled led_count."""
    value, response = extract_value(request.POST)
    if not 2 <= int(value) <= 490:
        return HttpResponseBadRequest("must be between 2 and 490")
    storage.put("wled_led_count", int(value))
    _notify_settings_changed("wled")
    return response


@control
def set_wled_ip(request: WSGIRequest) -> HttpResponse:
    """Updates the wled ip."""
    value, response = extract_value(request.POST)
    try:
        socket.inet_aton(value)
    except socket.error:
        return HttpResponseBadRequest("invalid ip")
    storage.put("wled_ip", value)
    _notify_settings_changed("wled")
    return response


@control
def set_wled_port(request: WSGIRequest) -> HttpResponse:
    """Updates the wled port."""
    value, response = extract_value(request.POST)
    if not 1024 <= int(value) <= 65535:
        return HttpResponseBadRequest("invalid port")
    storage.put("wled_port", int(value))
    _notify_settings_changed("wled")
    return response


@control
def set_wled_program(request: WSGIRequest) -> HttpResponse:
    """Updates the wled program."""
    return _handle_program_request("wled", request)


@control
def set_wled_brightness(request: WSGIRequest) -> HttpResponse:
    """Updates the wled brightness."""
    return _handle_brightness_request("wled", request)


@control
def set_wled_monochrome(request: WSGIRequest) -> HttpResponse:
    """Sets whether the wled should be in one color only."""
    return _handle_monochrome_request("wled", request)


@control
def set_strip_program(request: WSGIRequest) -> HttpResponse:
    """Updates the strip program."""
    return _handle_program_request("strip", request)


@control
def set_strip_brightness(request: WSGIRequest) -> HttpResponse:
    """Updates the strip brightness."""
    return _handle_brightness_request("strip", request)


@control
def adjust_screen(_request: WSGIRequest) -> None:
    """Adjusts the resolution of the screen."""
    _notify_settings_changed("adjust_screen")


@control
def set_screen_program(request: WSGIRequest) -> HttpResponse:
    """Updates the screen program."""
    return _handle_program_request("screen", request)


@control
def set_initial_resolution(request: WSGIRequest) -> HttpResponse:
    """Sets the resolution used on the screen."""
    value, response = extract_value(request.POST)
    resolution = tuple(map(int, value.split("x")))
    resolution = cast(Tuple[int, int], resolution)
    storage.put("initial_resolution", resolution)
    # adjusting sets the resolution and restarts the screen program
    _notify_settings_changed("adjust_screen")
    return response


@control
def set_dynamic_resolution(request: WSGIRequest) -> HttpResponse:
    """Sets whether the resolution should be dynamically adjusted depending on the performance."""
    value, response = extract_value(request.POST)
    storage.put("dynamic_resolution", strtobool(value))
    _notify_settings_changed("base")
    return response
