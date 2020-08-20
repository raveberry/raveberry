"""This module contains everything related to the settings and configuration of the server."""
# pylint: disable=no-self-use  # self is used in decorator

from __future__ import annotations

import configparser
import os
import socket
import subprocess
from functools import wraps
from typing import Callable, Dict, Any, TYPE_CHECKING, Optional, TypeVar

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect

from core.models import Setting
from core.state_handler import Stateful

if TYPE_CHECKING:
    from core.base import Base
    from core.settings.basic import Basic
    from core.settings.platforms import Platforms
    from core.settings.sound import Sound
    from core.settings.wifi import Wifi
    from core.settings.library import Library
    from core.settings.analysis import Analysis
    from core.settings.system import System

    T = TypeVar(  # pylint: disable=invalid-name
        "T", Basic, Platforms, Sound, Wifi, Library, Analysis, System
    )


class Settings(Stateful):
    """This class is responsible for handling requests from the /settings page."""

    @staticmethod
    def get_setting(key: str, default: str) -> str:
        """This method returns the value for the given :param key:.
        Vaules of non-existing keys are set to :param default:"""
        if settings.MOCK:
            return default
        else:
            return Setting.objects.get_or_create(key=key, defaults={"value": default})[
                0
            ].value

    @staticmethod
    def option(
        func: Callable[[T, WSGIRequest], Optional[HttpResponse]]
    ) -> Callable[[T, WSGIRequest], HttpResponse]:
        """A decorator that makes sure that only the admin changes a setting."""

        def _decorator(self: T, request: WSGIRequest) -> HttpResponse:
            # don't allow option changes during alarm
            if not self.base.user_manager.is_admin(request.user):
                return HttpResponseForbidden()
            response = func(self, request)
            self.base.settings.update_state()
            if response is not None:
                return response
            return HttpResponse()

        return wraps(func)(_decorator)

    def __init__(self, base: "Base") -> None:
        from core.settings.basic import Basic
        from core.settings.platforms import Platforms
        from core.settings.sound import Sound
        from core.settings.wifi import Wifi
        from core.settings.library import Library
        from core.settings.analysis import Analysis
        from core.settings.system import System

        self.base = base
        self.basic = Basic(base)
        self.platforms = Platforms(base)
        self.sound = Sound(base)
        self.wifi = Wifi(base)
        self.library = Library(base)
        self.analysis = Analysis(base)
        self.system = System(base)

    def state_dict(self) -> Dict[str, Any]:
        state_dict = self.base.state_dict()
        state_dict["voting_system"] = self.basic.voting_system
        state_dict["new_music_only"] = self.basic.new_music_only
        state_dict["logging_enabled"] = self.basic.logging_enabled
        state_dict["online_suggestions"] = self.basic.online_suggestions
        state_dict["number_of_suggestions"] = self.basic.number_of_suggestions
        state_dict["people_to_party"] = self.basic.people_to_party
        state_dict["alarm_probability"] = self.basic.alarm_probability
        state_dict["downvotes_to_kick"] = self.basic.downvotes_to_kick
        state_dict["max_download_size"] = self.basic.max_download_size
        state_dict["additional_keywords"] = self.basic.additional_keywords
        state_dict["forbidden_keywords"] = self.basic.forbidden_keywords
        state_dict["max_playlist_items"] = self.basic.max_playlist_items
        state_dict["has_internet"] = self.basic.has_internet

        state_dict["youtube_enabled"] = self.platforms.youtube_enabled
        state_dict["youtube_suggestions"] = self.platforms.youtube_suggestions

        state_dict["spotify_enabled"] = self.platforms.spotify_enabled
        state_dict["spotify_suggestions"] = self.platforms.spotify_suggestions

        state_dict["soundcloud_enabled"] = self.platforms.soundcloud_enabled
        state_dict["soundcloud_suggestions"] = self.platforms.soundcloud_suggestions

        state_dict["bluetooth_scanning"] = self.sound.bluetoothctl is not None
        state_dict["bluetooth_devices"] = self.sound.bluetooth_devices

        try:
            with open(os.path.join(settings.BASE_DIR, "config/homewifi")) as f:
                state_dict["homewifi_ssid"] = f.read()
        except FileNotFoundError:
            state_dict["homewifi_ssid"] = ""

        state_dict["scan_progress"] = self.library.scan_progress

        if settings.DOCKER and not settings.DOCKER_ICECAST:
            # icecast is definitely disabled
            streaming_enabled = False
        else:
            # the icecast service reports as active even if it is internally disabled.
            # check if its port is used to determine if it's running
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                streaming_enabled = sock.connect_ex((settings.ICECAST_HOST, 8000)) == 0
        state_dict["streaming_enabled"] = streaming_enabled

        try:
            state_dict["homewifi_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/homewifi_enabled"]) != 0
            )
            state_dict["events_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/events_enabled"]) != 0
            )
            state_dict["hotspot_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/hotspot_enabled"]) != 0
            )
            state_dict["wifi_protected"] = (
                subprocess.call(["/usr/local/sbin/raveberry/wifi_protected"]) != 0
            )
            state_dict["tunneling_enabled"] = (
                subprocess.call(["sudo", "/usr/local/sbin/raveberry/tunneling_enabled"])
                != 0
            )
            state_dict["remote_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/remote_enabled"]) != 0
            )
        except FileNotFoundError:
            state_dict["system_install"] = False
        else:
            state_dict["system_install"] = True
            config = configparser.ConfigParser()
            config.read(os.path.join(settings.BASE_DIR, "config/raveberry.ini"))
            state_dict["hotspot_configured"] = config.getboolean("Modules", "hotspot")
            state_dict["remote_configured"] = config["Remote"]["remote_key"] != ""

        return state_dict

    def index(self, request: WSGIRequest) -> HttpResponse:
        """Renders the /settings page. Only admin is allowed to see this page."""
        if not self.base.user_manager.is_admin(request.user):
            return redirect("login")
        context = self.base.context(request)
        library_path = self.library.get_library_path()
        if os.path.islink(library_path):
            context["local_library"] = os.readlink(library_path)
        else:
            context["local_library"] = "/"
        context["version"] = settings.VERSION
        return render(request, "settings.html", context)
