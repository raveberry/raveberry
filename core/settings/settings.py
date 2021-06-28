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
        settings_state["votingSystem"] = self.basic.voting_system
        settings_state["newMusicOnly"] = self.basic.new_music_only
        settings_state["loggingEnabled"] = self.basic.logging_enabled
        settings_state["embedStream"] = self.basic.embed_stream
        settings_state["dynamicEmbeddedStream"] = self.basic.dynamic_embedded_stream
        settings_state["hashtagsActive"] = self.basic.hashtags_active
        settings_state["onlineSuggestions"] = self.basic.online_suggestions
        settings_state["numberOfSuggestions"] = self.basic.number_of_suggestions
        settings_state["peopleToParty"] = self.basic.people_to_party
        settings_state["alarmProbability"] = self.basic.alarm_probability
        settings_state["buzzerCooldown"] = self.basic.buzzer_cooldown
        settings_state["downvotesToKick"] = self.basic.downvotes_to_kick
        settings_state["maxDownloadSize"] = self.basic.max_download_size
        settings_state["additionalKeywords"] = self.basic.additional_keywords
        settings_state["forbiddenKeywords"] = self.basic.forbidden_keywords
        settings_state["maxPlaylistItems"] = self.basic.max_playlist_items
        settings_state["maxQueueLength"] = self.basic.max_queue_length
        settings_state["hasInternet"] = self.basic.has_internet

        settings_state["youtubeEnabled"] = self.platforms.youtube_enabled
        settings_state["youtubeSuggestions"] = self.platforms.youtube_suggestions

        settings_state["spotifyEnabled"] = self.platforms.spotify_enabled
        settings_state["spotifySuggestions"] = self.platforms.spotify_suggestions

        settings_state["soundcloudEnabled"] = self.platforms.soundcloud_enabled
        settings_state["soundcloudSuggestions"] = self.platforms.soundcloud_suggestions

        settings_state["jamendoEnabled"] = self.platforms.jamendo_enabled
        settings_state["jamendoSuggestions"] = self.platforms.jamendo_suggestions

        settings_state["backupStream"] = self.sound.backup_stream

        settings_state["bluetoothScanning"] = self.sound.bluetoothctl is not None
        settings_state["bluetoothDevices"] = self.sound.bluetooth_devices

        settings_state["feedCava"] = self.sound.feed_cava
        settings_state["output"] = self.sound.output

        try:
            with open(os.path.join(settings.BASE_DIR, "config/homewifi")) as f:
                settings_state["homewifiSsid"] = f.read()
        except FileNotFoundError:
            settings_state["homewifiSsid"] = ""

        settings_state["scanProgress"] = self.library.scan_progress

        try:
            settings_state["homewifiEnabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/homewifi_enabled"]) != 0
            )
            settings_state["eventsEnabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/events_enabled"]) != 0
            )
            settings_state["hotspotEnabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/hotspot_enabled"]) != 0
            )
            settings_state["wifiProtectionEnabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/wifi_protection_enabled"])
                != 0
            )
            settings_state["tunnelingEnabled"] = (
                subprocess.call(["sudo", "/usr/local/sbin/raveberry/tunneling_enabled"])
                != 0
            )
            settings_state["remoteEnabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/remote_enabled"]) != 0
            )
        except FileNotFoundError:
            settings_state["systemInstall"] = False
        else:
            settings_state["systemInstall"] = True
            with open(os.path.join(settings.BASE_DIR, "config/raveberry.yaml")) as f:
                config = yaml.safe_load(f)
            settings_state["hotspotConfigured"] = config["hotspot"]
            settings_state["remoteConfigured"] = config["remote_key"] is not None

        settings_state["youtubeConfigured"] = self.platforms.youtube_available
        settings_state["spotifyConfigured"] = self.platforms.spotify_available
        settings_state["soundcloudConfigured"] = self.platforms.soundcloud_available
        settings_state["jamendoConfigured"] = self.platforms.jamendo_available

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
