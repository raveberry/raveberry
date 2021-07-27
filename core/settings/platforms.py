"""This module handles all settings regarding the music platforms."""
from __future__ import annotations

import importlib
import os
import subprocess

from django.conf import settings as conf
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.http import HttpResponseBadRequest

from core import redis
from core.settings import library, system
from core.settings.settings import control
from core.settings import storage


def start() -> None:
    """Initializes this module by checking which platforms are available to use."""

    # local songs are enabled if a library is set
    local_enabled = os.path.islink(library.get_library_path())
    storage.set("local_enabled", local_enabled)

    # in the docker container all dependencies are installed
    youtube_available = (
        conf.DOCKER or importlib.util.find_spec("youtube_dl") is not None
    )
    redis.set("youtube_available", youtube_available)
    if not youtube_available:
        # if youtube is not available, overwrite the database to disable it
        storage.set("youtube_enabled", False)

    # Spotify has no python dependencies we could easily check.
    try:
        spotify_available = (
            conf.DOCKER
            or "[spotify]"
            in subprocess.check_output(["mopidy", "config"], stderr=subprocess.DEVNULL)
            .decode()
            .splitlines()
        )
    except FileNotFoundError:
        # mopidy is not installed (eg in docker). Since we can't check, enable
        spotify_available = True
    redis.set("spotify_available", spotify_available)
    if not spotify_available:
        storage.set("spotify_enabled", False)

    soundcloud_available = (
        conf.DOCKER or importlib.util.find_spec("soundcloud") is not None
    )
    redis.set("soundcloud_available", soundcloud_available)
    if not soundcloud_available:
        storage.set("soundcloud_enabled", False)

    # Jamendo has no python dependencies we could easily check.
    try:
        jamendo_available = (
            conf.DOCKER
            or "[jamendo]"
            in subprocess.check_output(["mopidy", "config"], stderr=subprocess.DEVNULL)
            .decode()
            .splitlines()
        )
    except FileNotFoundError:
        jamendo_available = True
    redis.set("jamendo_available", jamendo_available)
    if not jamendo_available:
        storage.set("jamendo_enabled", False)


@control
def set_youtube_enabled(request: WSGIRequest):
    """Enables or disables youtube to be used as a song provider."""
    enabled = request.POST.get("value") == "true"
    storage.set("youtube_enabled", enabled)


@control
def set_youtube_suggestions(request: WSGIRequest):
    """Sets the number of online suggestions from youtube to be shown."""
    value = int(request.POST.get("value"))  # type: ignore
    storage.set("youtube_suggestions", value)


def _set_extension_enabled(extension, enabled) -> HttpResponse:
    if enabled:
        if conf.DOCKER:
            response = HttpResponse(
                "Make sure you provided mopidy with correct credentials."
            )
        else:
            extensions = system.check_mopidy_extensions()
            functional, message = extensions[extension]
            if not functional:
                return HttpResponseBadRequest(message)
            response = HttpResponse(message)
    else:
        response = HttpResponse("Disabled extension")
    storage.set(f"{extension}_enabled", enabled)
    return response


@control
def set_spotify_enabled(request: WSGIRequest) -> HttpResponse:
    """Enables or disables spotify to be used as a song provider.
    Makes sure mopidy has correct spotify configuration."""
    enabled = request.POST.get("value") == "true"
    return _set_extension_enabled("spotify", enabled)


@control
def set_spotify_suggestions(request: WSGIRequest):
    """Sets the number of online suggestions from spotify to be shown."""
    value = int(request.POST.get("value"))  # type: ignore
    storage.set("spotify_suggestions", value)


@control
def set_spotify_credentials(request: WSGIRequest) -> HttpResponse:
    """Update spotify credentials."""
    username = request.POST.get("username")
    password = request.POST.get("password")
    client_id = request.POST.get("client_id")
    client_secret = request.POST.get("client_secret")

    if not username or not password or not client_id or not client_secret:
        return HttpResponseBadRequest("All fields are required")

    storage.set("spotify_username", username)
    storage.set("spotify_password", password)
    storage.set("spotify_client_id", client_id)
    storage.set("spotify_client_secret", client_secret)

    system.update_mopidy_config("pulse")
    return HttpResponse("Updated credentials")


@control
def set_soundcloud_enabled(request: WSGIRequest) -> HttpResponse:
    """Enables or disables soundcloud to be used as a song provider.
    Makes sure mopidy has correct soundcloud configuration."""
    enabled = request.POST.get("value") == "true"
    return _set_extension_enabled("soundcloud", enabled)


@control
def set_soundcloud_suggestions(request: WSGIRequest):
    """Sets the number of online suggestions from soundcloud to be shown."""
    value = int(request.POST.get("value"))  # type: ignore
    storage.set("soundcloud_suggestions", value)


@control
def set_soundcloud_credentials(request: WSGIRequest) -> HttpResponse:
    """Update soundcloud credentials."""
    auth_token = request.POST.get("auth_token")

    if not auth_token:
        return HttpResponseBadRequest("All fields are required")

    storage.set("soundcloud_auth_token", auth_token)

    system.update_mopidy_config("pulse")
    return HttpResponse("Updated credentials")


@control
def set_jamendo_enabled(request: WSGIRequest) -> HttpResponse:
    """Enables or disables jamendo to be used as a song provider.
    Makes sure mopidy has correct jamendo configuration."""
    enabled = request.POST.get("value") == "true"
    return _set_extension_enabled("jamendo", enabled)


@control
def set_jamendo_suggestions(request: WSGIRequest):
    """Sets the number of online suggestions from jamendo to be shown."""
    value = int(request.POST.get("value"))  # type: ignore
    storage.set("jamendo_suggestions", value)


@control
def set_jamendo_credentials(request: WSGIRequest) -> HttpResponse:
    """Update jamendo credentials."""
    client_id = request.POST.get("client_id")

    if not client_id:
        return HttpResponseBadRequest("All fields are required")

    storage.set("jamendo_client_id", client_id)

    system.update_mopidy_config("pulse")
    return HttpResponse("Updated credentials")
