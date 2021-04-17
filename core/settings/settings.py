"""This module contains everything related to the settings and configuration of the server."""
# pylint: disable=no-self-use  # self is used in decorator

from __future__ import annotations

import os
import subprocess
import yaml
from functools import wraps
from typing import Callable, Dict, Any, TYPE_CHECKING, Optional, TypeVar, List

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest

# JsonResponse needs to be imported here so types can resolved through the decorator?
from django.http import HttpResponse, JsonResponse
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import URLPattern

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
            if not self.settings.base.user_manager.is_admin(request.user):
                return HttpResponseForbidden()
            response = func(self, request)
            self.settings.update_state()
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
        self.urlpatterns: List[URLPattern] = []
        self.basic = Basic(self)
        self.platforms = Platforms(self)
        self.sound = Sound(self)
        self.wifi = Wifi(self)
        self.library = Library(self)
        self.analysis = Analysis(self)
        self.system = System(self)

    def state_dict(self) -> Dict[str, Any]:
        state_dict = self.base.state_dict()

        settings_state = {}
        settings_state["voting_system"] = self.basic.voting_system
        settings_state["new_music_only"] = self.basic.new_music_only
        settings_state["logging_enabled"] = self.basic.logging_enabled
        settings_state["online_suggestions"] = self.basic.online_suggestions
        settings_state["number_of_suggestions"] = self.basic.number_of_suggestions
        settings_state["people_to_party"] = self.basic.people_to_party
        settings_state["alarm_probability"] = self.basic.alarm_probability
        settings_state["downvotes_to_kick"] = self.basic.downvotes_to_kick
        settings_state["max_download_size"] = self.basic.max_download_size
        settings_state["additional_keywords"] = self.basic.additional_keywords
        settings_state["forbidden_keywords"] = self.basic.forbidden_keywords
        settings_state["max_playlist_items"] = self.basic.max_playlist_items
        settings_state["has_internet"] = self.basic.has_internet

        settings_state["youtube_enabled"] = self.platforms.youtube_enabled
        settings_state["youtube_suggestions"] = self.platforms.youtube_suggestions

        settings_state["spotify_enabled"] = self.platforms.spotify_enabled
        settings_state["spotify_suggestions"] = self.platforms.spotify_suggestions

        settings_state["soundcloud_enabled"] = self.platforms.soundcloud_enabled
        settings_state["soundcloud_suggestions"] = self.platforms.soundcloud_suggestions

        settings_state["backup_stream"] = self.sound.backup_stream

        settings_state["bluetooth_scanning"] = self.sound.bluetoothctl is not None
        settings_state["bluetooth_devices"] = self.sound.bluetooth_devices

        settings_state["output"] = self.sound.output

        try:
            with open(os.path.join(settings.BASE_DIR, "config/homewifi")) as f:
                settings_state["homewifi_ssid"] = f.read()
        except FileNotFoundError:
            settings_state["homewifi_ssid"] = ""

        settings_state["scan_progress"] = self.library.scan_progress

        try:
            settings_state["homewifi_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/homewifi_enabled"]) != 0
            )
            settings_state["events_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/events_enabled"]) != 0
            )
            settings_state["hotspot_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/hotspot_enabled"]) != 0
            )
            settings_state["wifi_protection_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/wifi_protection_enabled"])
                != 0
            )
            settings_state["tunneling_enabled"] = (
                subprocess.call(["sudo", "/usr/local/sbin/raveberry/tunneling_enabled"])
                != 0
            )
            settings_state["remote_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/remote_enabled"]) != 0
            )
        except FileNotFoundError:
            settings_state["system_install"] = False
        else:
            settings_state["system_install"] = True
            with open(os.path.join(settings.BASE_DIR, "config/raveberry.yaml")) as f:
                config = yaml.safe_load(f)
            settings_state["hotspot_configured"] = config["hotspot"]
            settings_state["remote_configured"] = config["remote_key"] is not None

        settings_state["youtube_configured"] = self.platforms.youtube_available
        settings_state["spotify_configured"] = self.platforms.spotify_available
        settings_state["soundcloud_configured"] = self.platforms.soundcloud_available

        state_dict["settings"] = settings_state
        return state_dict

    def index(self, request: WSGIRequest) -> HttpResponse:
        """Renders the /settings page. Only admin is allowed to see this page."""
        if not self.base.user_manager.is_admin(request.user):
            return redirect("login")
        context = self.base.context(request)
        context["urls"] = self.urlpatterns
        library_path = self.library.get_library_path()
        if os.path.islink(library_path):
            context["local_library"] = os.readlink(library_path)
        else:
            context["local_library"] = "/"
        context["version"] = settings.VERSION
        return render(request, "settings.html", context)
