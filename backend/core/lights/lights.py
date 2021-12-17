"""This module handles the basic endpoints led and screen visualizations."""

from __future__ import annotations

from typing import Dict, Any

from django.contrib.auth.decorators import user_passes_test
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render

from core import user_manager, base, redis
from core.settings import storage
from core.state_handler import send_state


def state_dict() -> Dict[str, Any]:
    state = base.state_dict()

    lights_state = {}
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
    lights_state["programSpeed"] = storage.get("program_speed")
    lights_state["fixedColor"] = "#{:02x}{:02x}{:02x}".format(
        *(int(val * 255) for val in storage.get("fixed_color"))
    )

    state["lights"] = lights_state
    return state


@user_passes_test(user_manager.has_controls)
def index(request: WSGIRequest) -> HttpResponse:
    """Renders the /lights page. During voting, only privileged users can access this."""
    from core import urls

    context = base.context(request)
    context["urls"] = urls.lights_paths
    # programs that have a strip_color or ring_color function are color programs
    # programs that have a draw function are screen programs
    context["color_program_names"] = ["Disabled", "Fixed", "Rainbow", "Rave"]
    context["screen_program_names"] = ["Disabled", "Circular"]
    return render(request, "lights.html", context)


def update_state() -> None:
    """Sends an update event to all connected clients."""
    send_state(state_dict())
