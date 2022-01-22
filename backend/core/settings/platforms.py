"""This module handles all settings regarding the music platforms."""
from __future__ import annotations

import importlib.util
import os
import subprocess
from typing import cast

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseBadRequest

from django.conf import settings as conf
from core import redis
from core.settings import library, storage, system
from core.settings.settings import control
from core.settings.storage import PlatformEnabled
from core.util import extract_value, strtobool


def start() -> None:
    """Initializes this module by checking which platforms are available to use."""

    # local songs are enabled if a library is set
    local_enabled = os.path.islink(library.get_library_path())
    storage.put("local_enabled", local_enabled)

    # in the docker container all dependencies are installed
    youtube_available = conf.DOCKER or importlib.util.find_spec("yt_dlp") is not None
    redis.put("youtube_available", youtube_available)
    if not youtube_available:
        # if youtube is not available, overwrite the database to disable it
        storage.put("youtube_enabled", False)

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
    redis.put("spotify_available", spotify_available)
    if not spotify_available:
        storage.put("spotify_enabled", False)

    soundcloud_available = (
        conf.DOCKER or importlib.util.find_spec("soundcloud") is not None
    )
    redis.put("soundcloud_available", soundcloud_available)
    if not soundcloud_available:
        storage.put("soundcloud_enabled", False)

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
    redis.put("jamendo_available", jamendo_available)
    if not jamendo_available:
        storage.put("jamendo_enabled", False)


@control
def set_youtube_enabled(request: WSGIRequest) -> HttpResponse:
    """Enables or disables youtube to be used as a song provider."""
    value, response = extract_value(request.POST)
    storage.put("youtube_enabled", strtobool(value))
    return response


@control
def set_youtube_suggestions(request: WSGIRequest) -> HttpResponse:
    """Sets the number of online suggestions from youtube to be shown."""
    value, response = extract_value(request.POST)
    storage.put("youtube_suggestions", int(value))
    return response


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
    assert extension in ["local", "youtube", "spotify", "soundcloud", "jamendo"]
    storage.put(cast(PlatformEnabled, f"{extension}_enabled"), enabled)
    return response


@control
def set_spotify_enabled(request: WSGIRequest) -> HttpResponse:
    """Enables or disables spotify to be used as a song provider.
    Makes sure mopidy has correct spotify configuration."""
    value, _ = extract_value(request.POST)
    return _set_extension_enabled("spotify", strtobool(value))


@control
def set_spotify_suggestions(request: WSGIRequest) -> HttpResponse:
    """Sets the number of online suggestions from spotify to be shown."""
    value, response = extract_value(request.POST)
    storage.put("spotify_suggestions", int(value))
    return response


@control
def set_spotify_credentials(request: WSGIRequest) -> HttpResponse:
    """Update spotify credentials."""
    username = request.POST.get("username")
    password = request.POST.get("password")
    client_id = request.POST.get("client_id")
    client_secret = request.POST.get("client_secret")

    if not username or not password or not client_id or not client_secret:
        return HttpResponseBadRequest("All fields are required")

    storage.put("spotify_username", username)
    storage.put("spotify_password", password)
    storage.put("spotify_client_id", client_id)
    storage.put("spotify_client_secret", client_secret)

    system.update_mopidy_config("pulse")
    return HttpResponse("Updated credentials")


@control
def set_soundcloud_enabled(request: WSGIRequest) -> HttpResponse:
    """Enables or disables soundcloud to be used as a song provider.
    Makes sure mopidy has correct soundcloud configuration."""
    value, _ = extract_value(request.POST)
    return _set_extension_enabled("soundcloud", strtobool(value))


@control
def set_soundcloud_suggestions(request: WSGIRequest) -> HttpResponse:
    """Sets the number of online suggestions from soundcloud to be shown."""
    value, response = extract_value(request.POST)
    storage.put("soundcloud_suggestions", int(value))
    return response


@control
def set_soundcloud_credentials(request: WSGIRequest) -> HttpResponse:
    """Update soundcloud credentials."""
    auth_token = request.POST.get("auth_token")

    if not auth_token:
        return HttpResponseBadRequest("All fields are required")

    storage.put("soundcloud_auth_token", auth_token)

    system.update_mopidy_config("pulse")
    return HttpResponse("Updated credentials")


@control
def set_jamendo_enabled(request: WSGIRequest) -> HttpResponse:
    """Enables or disables jamendo to be used as a song provider.
    Makes sure mopidy has correct jamendo configuration."""
    value, _ = extract_value(request.POST)
    return _set_extension_enabled("jamendo", strtobool(value))


@control
def set_jamendo_suggestions(request: WSGIRequest) -> HttpResponse:
    """Sets the number of online suggestions from jamendo to be shown."""
    value, response = extract_value(request.POST)
    storage.put("jamendo_suggestions", int(value))
    return response


@control
def set_jamendo_credentials(request: WSGIRequest) -> HttpResponse:
    """Update jamendo credentials."""
    client_id = request.POST.get("client_id")

    if not client_id:
        return HttpResponseBadRequest("All fields are required")

    storage.put("jamendo_client_id", client_id)

    system.update_mopidy_config("pulse")
    return HttpResponse("Updated credentials")
