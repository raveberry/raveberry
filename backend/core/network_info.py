"""This module handles requests for the network info page."""

from __future__ import annotations

import io
import subprocess
from typing import Any, Dict, Optional

import qrcode
from django.contrib.auth.decorators import user_passes_test
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render

from core import base, user_manager, util


def state_dict() -> Dict[str, Any]:
    """Extends the base state with network_info-specific information (none) and returns it."""
    state = base.state_dict()
    return state


def _qr_path(data) -> str:
    # from https://github.com/lincolnloop/python-qrcode/blob/master/qrcode/console_scripts.py
    module = "qrcode.image.svg.SvgPathImage"
    module, name = module.rsplit(".", 1)
    imp = __import__(module, {}, {}, [name])
    svg_path_image = getattr(imp, name)

    qr_code = qrcode.QRCode()
    qr_code.add_data(data)
    img = qr_code.make_image(image_factory=svg_path_image)
    with io.BytesIO() as stream:
        img.save(stream)
        svg = stream.getvalue().decode()
    tag = svg.split("\n")[1]
    return tag


def _add_hotspot_context(context: Dict[str, Any]) -> None:
    context["hotspot_enabled"] = False
    try:
        if subprocess.call(["/usr/local/sbin/raveberry/hotspot_enabled"]) != 0:
            # Hotspot is enabled, show its info as well
            context["hotspot_enabled"] = True

            with open(
                "/etc/hostapd/hostapd_protected.conf", encoding="utf-8"
            ) as hostapd_file:
                for line in hostapd_file:
                    line = line.strip()
                    if line.startswith("ssid"):
                        hotspot_ssid = line.split("=")[1]
                    if line.startswith("wpa_passphrase"):
                        hotspot_password = line.split("=")[1]

            device = util.get_devices()[-1]
            ip = util.ip_of_device(device)
            url = f"http://{ip}/"

            context["hotspot_ssid"] = hotspot_ssid
            context["hotspot_password"] = hotspot_password
            context["hotspot_wifi_qr"] = _qr_path(
                f"WIFI:S:{hotspot_ssid};T:WPA;P:{hotspot_password};;"
            )
            context["hotspot_url"] = url
            context["hotspot_url_qr"] = _qr_path(url)
            context["hotspot_ip"] = ip
    except FileNotFoundError:
        # hotspot was not configured
        pass


@user_passes_test(user_manager.has_controls)
def index(request: WSGIRequest) -> HttpResponse:
    """Renders the /network_info page. Only admin is allowed to see this page."""
    context = base.context(request)

    _add_hotspot_context(context)

    # connected network information
    ssid: Optional[str] = None
    password: Optional[str] = None
    try:
        ssid = subprocess.check_output(
            "/sbin/iwgetid --raw".split(), universal_newlines=True
        )[:-1]
        wifi_active = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        wifi_active = False

    if wifi_active:
        assert ssid
        try:
            password = subprocess.check_output(
                ["sudo", "/usr/local/sbin/raveberry/password_for_ssid", ssid],
                universal_newlines=True,
            )
        except subprocess.CalledProcessError:
            pass

    device = util.get_devices()[0]
    ip = util.ip_of_device(device)

    wifi_qr = _qr_path(f"WIFI:S:{ssid};T:WPA;P:{password};;")
    raveberry_url = f"http://{ip}/"
    raveberry_qr = _qr_path(raveberry_url)

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
