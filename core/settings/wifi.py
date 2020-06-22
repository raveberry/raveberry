"""This module handles all settings related to wifi."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse

from core.settings.settings import Settings

if TYPE_CHECKING:
    from core.base import Base


class Wifi:
    """This class is responsible for handling settings changes related to wifi."""

    def __init__(self, base: "Base"):
        self.base = base

    @Settings.option
    def available_ssids(self, _request: WSGIRequest) -> JsonResponse:
        """List all ssids that can currently be seen."""
        output = subprocess.check_output(
            ["sudo", "/usr/local/sbin/raveberry/list_available_ssids"]
        ).decode()
        ssids = output.split("\n")
        return JsonResponse(ssids[:-1], safe=False)

    @Settings.option
    def connect_to_wifi(self, request: WSGIRequest) -> HttpResponse:
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

    @Settings.option
    def disable_homewifi(self, _request: WSGIRequest) -> None:
        """Disable homewifi function."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_homewifi"])

    @Settings.option
    def enable_homewifi(self, _request: WSGIRequest) -> None:
        """Enable homewifi function."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_homewifi"])

    @Settings.option
    def stored_ssids(self, _request: WSGIRequest) -> JsonResponse:
        """Return the list of ssids that this Raspberry Pi was connected to in the past."""
        output = subprocess.check_output(
            ["sudo", "/usr/local/sbin/raveberry/list_stored_ssids"]
        ).decode()
        ssids = output.split("\n")
        return JsonResponse(ssids[:-1], safe=False)

    @Settings.option
    def set_homewifi_ssid(self, request: WSGIRequest) -> HttpResponse:
        """Set the home network.
        The hotspot will not be created if connected to this wifi."""
        homewifi_ssid = request.POST.get("homewifi_ssid")
        if homewifi_ssid is None:
            return HttpResponseBadRequest("homewifi ssid was not supplied.")
        with open(os.path.join(settings.BASE_DIR, "config/homewifi"), "w+") as f:
            f.write(homewifi_ssid)
        return HttpResponse()
