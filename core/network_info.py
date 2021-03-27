"""This module handles requests for the network info page."""

from __future__ import annotations

import io
import os
import subprocess
from typing import Any, TYPE_CHECKING, Dict

import configparser
import qrcode
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render, redirect

from core import util
from core.state_handler import Stateful
from main import settings

if TYPE_CHECKING:
    from core.base import Base


class NetworkInfo(Stateful):
    """This class handles requests on the /network_info page."""

    def __init__(self, base: "Base"):
        self.base = base

    def state_dict(self) -> Dict[str, Any]:
        state_dict = self.base.state_dict()
        return state_dict

    def _qr_path(self, data) -> str:
        # from https://github.com/lincolnloop/python-qrcode/blob/master/qrcode/console_scripts.py
        module = "qrcode.image.svg.SvgPathImage"
        module, name = module.rsplit(".", 1)
        imp = __import__(module, {}, [], [name])
        SvgPathImage = getattr(imp, name)

        qr = qrcode.QRCode()
        qr.add_data(data)
        img = qr.make_image(image_factory=SvgPathImage)
        with io.BytesIO() as stream:
            img.save(stream)
            svg = stream.getvalue().decode()
        tag = svg.split("\n")[1]
        return tag

    def index(self, request: WSGIRequest) -> HttpResponse:
        """Renders the /network_info page. Only admin is allowed to see this page."""
        if not self.base.user_manager.is_admin(request.user):
            return redirect("login")
        context = self.base.context(request)

        # hotspot information
        context["hotspot_enabled"] = False
        try:
            if subprocess.call(["/usr/local/sbin/raveberry/hotspot_enabled"]) != 0:
                # Hotspot is enabled, show its info as well
                context["hotspot_enabled"] = True

                with open("/etc/hostapd/hostapd_protected.conf") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("ssid"):
                            ssid = line.split("=")[1]
                        if line.startswith("wpa_passphrase"):
                            password = line.split("=")[1]

                device = util.get_devices()[-1]
                ip = util.ip_of_device(device)
                url = f"http://{ip}/"

                context["hotspot_ssid"] = ssid
                context["hotspot_password"] = password
                context["hotspot_wifi_qr"] = self._qr_path(
                    f"WIFI:S:{ssid};T:WPA;P:{password};;"
                )
                context["hotspot_url"] = url
                context["hotspot_url_qr"] = self._qr_path(url)
                context["hotspot_ip"] = ip
        except FileNotFoundError:
            # hotspot was not configured
            pass

        # connected network information
        ssid = None
        password = None
        try:
            ssid = subprocess.check_output(
                "/sbin/iwgetid --raw".split(), universal_newlines=True
            )[:-1]
            wifi_active = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            wifi_active = False

        if wifi_active:
            try:
                password = subprocess.check_output(
                    ["sudo", "/usr/local/sbin/raveberry/password_for_ssid", ssid],
                    universal_newlines=True,
                )
            except subprocess.CalledProcessError:
                pass

        device = util.get_devices()[0]
        ip = util.ip_of_device(device)

        wifi_qr = self._qr_path(f"WIFI:S:{ssid};T:WPA;P:{password};;")
        raveberry_url = f"http://{ip}/"
        raveberry_qr = self._qr_path(raveberry_url)

        if wifi_active:
            context["ssid"] = ssid
            context["password"] = password
            context["wifi_qr"] = wifi_qr
        else:
            context["ssid"] = None
            context["password"] = None
            context["wifi_qr"] = None
        context["url"] = raveberry_url
        context["url_qr"] = raveberry_qr
        context["ip"] = ip
        return render(request, "network_info.html", context)
