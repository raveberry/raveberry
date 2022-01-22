"""This module handles the basic endpoints led and screen visualizations."""

from __future__ import annotations

from typing import Dict, Any

from django.contrib.auth.decorators import user_passes_test
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render

from core import user_manager, base, redis, util
from core.settings import storage
from core.state_handler import send_state


def state_dict() -> Dict[str, Any]:
    """Extends the base state with lights-specific information and returns it."""
    state = base.state_dict()

    lights_state: Dict[str, Any] = {}
    lights_state["ringConnected"] = redis.get("ring_initialized")
    lights_state["ringProgram"] = storage.get("ring_program")
    lights_state["ringBrightness"] = storage.get("ring_brightness")
    lights_state["ringMonochrome"] = storage.get("ring_monochrome")
    lights_state["wledLedCount"] = storage.get("wled_led_count")
    lights_state["wledIp"] = storage.get("wled_ip")
    lights_state["wledPort"] = storage.get("wled_port")
    lights_state["wledConnected"] = redis.get("wled_initialized")
    lights_state["wledProgram"] = storage.get("wled_program")
    lights_state["wledBrightness"] = storage.get("wled_brightness")
    lights_state["wledMonochrome"] = storage.get("wled_monochrome")
    lights_state["stripConnected"] = redis.get("strip_initialized")
    lights_state["stripProgram"] = storage.get("strip_program")
    lights_state["stripBrightness"] = storage.get("strip_brightness")
    lights_state["screenConnected"] = redis.get("screen_initialized")
    lights_state["screenProgram"] = storage.get("screen_program")
    lights_state["initialResolution"] = util.format_resolution(
        storage.get("initial_resolution")
    )
    lights_state["dynamicResolution"] = storage.get("dynamic_resolution")
    lights_state["currentResolution"] = util.format_resolution(
        redis.get("current_resolution")
    )
    lights_state["currentFps"] = f"{redis.get('current_fps'):.2f}"
    lights_state["ups"] = storage.get("ups")
    lights_state["programSpeed"] = storage.get("program_speed")
    red, green, blue = (int(val * 255) for val in storage.get("fixed_color"))
    lights_state["fixedColor"] = f"#{red:02x}{green:02x}{blue:02x}"

    state["lights"] = lights_state
    return state


@user_passes_test(user_manager.has_controls)
def index(request: WSGIRequest) -> HttpResponse:
    """Renders the /lights page. During voting, only privileged users can access this."""
    from core import urls

    context = base.context(request)
    context["urls"] = urls.lights_paths
    # programs that have a strip_color or ring_color function are color programs
    context["led_programs"] = redis.get("led_programs")
    context["screen_programs"] = redis.get("screen_programs")
    context["resolutions"] = [
        util.format_resolution(resolution) for resolution in redis.get("resolutions")
    ]
    return render(request, "lights.html", context)


def update_state() -> None:
    """Sends an update event to all connected clients."""
    send_state(state_dict())
