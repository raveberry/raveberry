"""This module handles all settings related to wifi."""

from __future__ import annotations

import os
import subprocess

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse

from core.settings.settings import control


@control
def available_ssids(_request: WSGIRequest) -> JsonResponse:
    """List all ssids that can currently be seen."""
    output = subprocess.check_output(
        ["sudo", "/usr/local/sbin/raveberry/list_available_ssids"]
    ).decode()
    ssids = output.split("\n")
    return JsonResponse(ssids[:-1], safe=False)


@control
def connect_to_wifi(request: WSGIRequest) -> HttpResponse:
    """Connect to a given ssid with the given password."""
    ssid = request.POST.get("ssid")
    password = request.POST.get("password")
    if ssid is None or password is None or ssid == "" or password == "":
        return HttpResponseBadRequest("Please provide both SSID and password")
    try:
        output = subprocess.check_output(
            ["sudo", "/usr/local/sbin/raveberry/connect_to_wifi", ssid, password]
        ).decode()
        return HttpResponse(output)
    except subprocess.CalledProcessError as e:
        output = e.output.decode()
        return HttpResponseBadRequest(output)


@control
def disable_homewifi(_request: WSGIRequest) -> None:
    """Disable homewifi function."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_homewifi"])


@control
def enable_homewifi(_request: WSGIRequest) -> None:
    """Enable homewifi function."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_homewifi"])


@control
def stored_ssids(_request: WSGIRequest) -> JsonResponse:
    """Return the list of ssids that this Raspberry Pi was connected to in the past."""
    output = subprocess.check_output(
        ["sudo", "/usr/local/sbin/raveberry/list_stored_ssids"]
    ).decode()
    ssids = output.split("\n")
    return JsonResponse(ssids[:-1], safe=False)


@control
def set_homewifi_ssid(request: WSGIRequest) -> HttpResponse:
    """Set the home network.
    The hotspot will not be created if connected to this wifi."""
    homewifi_ssid = request.POST.get("value")
    if homewifi_ssid is None:
        return HttpResponseBadRequest("homewifi ssid was not supplied.")
    with open(os.path.join(settings.BASE_DIR, "config/homewifi"), "w+") as f:
        f.write(homewifi_ssid)
    return HttpResponse()
