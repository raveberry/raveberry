"""This module handles all settings regarding the music platforms."""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.http import HttpResponseBadRequest

from core.models import Setting
from core.settings.settings import Settings

if TYPE_CHECKING:
    from core.base import Base


class Platforms:
    """This class is responsible for handling setting changes related to music platforms."""

    def __init__(self, base: "Base"):
        self.base = base
        self.youtube_enabled = Settings.get_setting("youtube_enabled", "True") == "True"
        self.spotify_enabled = (
            Settings.get_setting("spotify_enabled", "False") == "True"
        )
        self.spotify_username = Settings.get_setting("spotify_username", "")
        self.spotify_password = Settings.get_setting("spotify_password", "")
        self.spotify_client_id = Settings.get_setting("spotify_client_id", "")
        self.spotify_client_secret = Settings.get_setting("spotify_client_secret", "")
        self.soundcloud_enabled = (
            Settings.get_setting("soundcloud_enabled", "False") == "True"
        )
        self.soundcloud_auth_token = Settings.get_setting("soundcloud_auth_token", "")

    @Settings.option
    def set_youtube_enabled(self, request: WSGIRequest):
        """Enables or disables youtube to be used as a song provider."""
        enabled = request.POST.get("value") == "true"
        Setting.objects.filter(key="youtube_enabled").update(value=enabled)
        self.youtube_enabled = enabled

    def _set_extension_enabled(self, extension, enabled) -> HttpResponse:
        if enabled:
            if settings.DOCKER:
                response = HttpResponse(
                    "Make sure to use a mopidy config with correct credentials."
                )
            else:
                extensions = self.base.settings.system.check_mopidy_extensions()
                functional, message = extensions[extension]
                if not functional:
                    return HttpResponseBadRequest(message)
                response = HttpResponse(message)
        else:
            response = HttpResponse("Disabled extension")
        Setting.objects.filter(key=f"{extension}_enabled").update(value=enabled)
        setattr(self, f"{extension}_enabled", enabled)
        return response

    @Settings.option
    def set_spotify_enabled(self, request: WSGIRequest) -> HttpResponse:
        """Enables or disables spotify to be used as a song provider.
        Makes sure mopidy has correct spotify configuration."""
        enabled = request.POST.get("value") == "true"
        return self._set_extension_enabled("spotify", enabled)

    @Settings.option
    def set_spotify_credentials(self, request: WSGIRequest) -> HttpResponse:
        """Update spotify credentials."""
        username = request.POST.get("username")
        password = request.POST.get("password")
        client_id = request.POST.get("client_id")
        client_secret = request.POST.get("client_secret")

        if not username or not password or not client_id or not client_secret:
            return HttpResponseBadRequest("All fields are required")

        self.spotify_username = username
        self.spotify_password = password
        self.spotify_client_id = client_id
        self.spotify_client_secret = client_secret

        Setting.objects.filter(key="spotify_username").update(
            value=self.spotify_username
        )
        Setting.objects.filter(key="spotify_password").update(
            value=self.spotify_password
        )
        Setting.objects.filter(key="spotify_client_id").update(
            value=self.spotify_client_id
        )
        Setting.objects.filter(key="spotify_client_secret").update(
            value=self.spotify_client_secret
        )

        self.base.settings.system.update_mopidy_config()
        return HttpResponse("Updated credentials")

    @Settings.option
    def set_soundcloud_enabled(self, request: WSGIRequest) -> HttpResponse:
        """Enables or disables soundcloud to be used as a song provider.
        Makes sure mopidy has correct soundcloud configuration."""
        enabled = request.POST.get("value") == "true"
        return self._set_extension_enabled("soundcloud", enabled)

    @Settings.option
    def set_soundcloud_credentials(self, request: WSGIRequest) -> HttpResponse:
        """Update soundcloud credentials."""
        auth_token = request.POST.get("auth_token")

        if not auth_token:
            return HttpResponseBadRequest("All fields are required")

        self.soundcloud_auth_token = auth_token

        Setting.objects.filter(key="soundcloud_auth_token").update(
            value=self.soundcloud_auth_token
        )

        self.base.settings.system.update_mopidy_config()
        return HttpResponse("Updated credentials")
