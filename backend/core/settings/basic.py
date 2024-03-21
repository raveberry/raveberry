"""This module handles all basic settings."""

from __future__ import annotations

import subprocess

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseBadRequest

from core import redis, user_manager
from core.musiq import playback
from core.settings import storage
from core.settings.settings import control
from core.util import strtobool, extract_value


def start() -> None:
    """Initializes this module. Checks whether internet is accessible."""
    _check_internet()


def _check_internet() -> None:
    host = storage.get("connectivity_host")
    if not host:
        redis.put("has_internet", False)
        return
    response = subprocess.call(
        ["ping", "-c", "1", "-W", "3", host], stdout=subprocess.DEVNULL
    )
    if response == 0:
        redis.put("has_internet", True)
    else:
        redis.put("has_internet", False)


@control
def set_interactivity(request: WSGIRequest) -> HttpResponse:
    """Enables or disables voting based on the given value."""
    value, response = extract_value(request.POST)
    if value not in [
        getattr(storage.Interactivity, attr)
        for attr in dir(storage.Interactivity)
        if not attr.startswith("__")
    ]:
        return HttpResponseBadRequest("Invalid value")
    storage.put("interactivity", value)
    return response


@control
def set_color_indication(request: WSGIRequest) -> HttpResponse:
    """Enables or disables voting based on the given value."""
    value, response = extract_value(request.POST)
    if value not in [
        getattr(storage.Privileges, attr)
        for attr in dir(storage.Privileges)
        if not attr.startswith("__")
    ]:
        return HttpResponseBadRequest("Invalid value")
    storage.put("color_indication", value)
    return response


@control
def set_ip_checking(request: WSGIRequest) -> HttpResponse:
    """Enables or disables ip checking based on the given value."""
    value, response = extract_value(request.POST)
    storage.put("ip_checking", strtobool(value))
    return response


@control
def set_downvotes_to_kick(request: WSGIRequest) -> HttpResponse:
    """Sets the number of downvotes that are needed to remove a song from the queue."""
    value, response = extract_value(request.POST)
    storage.put("downvotes_to_kick", int(value))
    return response


@control
def set_logging_enabled(request: WSGIRequest) -> HttpResponse:
    """Enables or disables logging of requests and play logs based on the given value."""
    value, response = extract_value(request.POST)
    storage.put("logging_enabled", strtobool(value))
    return response


@control
def set_hashtags_active(request: WSGIRequest) -> HttpResponse:
    """Enables or disables logging of requests and play logs based on the given value."""
    value, response = extract_value(request.POST)
    storage.put("hashtags_active", strtobool(value))
    return response


@control
def set_privileged_stream(request: WSGIRequest) -> HttpResponse:
    """Enables or disables logging of requests and play logs based on the given value."""
    value, response = extract_value(request.POST)
    storage.put("privileged_stream", strtobool(value))
    return response


@control
def set_online_suggestions(request: WSGIRequest) -> HttpResponse:
    """Enables or disables online suggestions based on the given value."""
    value, response = extract_value(request.POST)
    storage.put("online_suggestions", strtobool(value))
    return response


@control
def set_number_of_suggestions(request: WSGIRequest) -> HttpResponse:
    """Set the number of archived suggestions based on the given value."""
    value, response = extract_value(request.POST)
    storage.put("number_of_suggestions", int(value))
    return response


@control
def set_connectivity_host(request: WSGIRequest) -> HttpResponse:
    """Sets the host that is pinged to check the internet connection."""
    value, response = extract_value(request.POST)
    storage.put("connectivity_host", value)
    return response


@control
def check_internet(_request: WSGIRequest) -> None:
    """Checks whether an internet connection exists and updates the internal state."""
    _check_internet()


@control
def update_user_count(_request: WSGIRequest) -> None:
    """Force an update on the active user count."""
    user_manager.update_user_count()


@control
def set_new_music_only(request: WSGIRequest) -> HttpResponse:
    """Enables or disables the new music only mode based on the given value."""
    value, response = extract_value(request.POST)
    storage.put("new_music_only", strtobool(value))
    return response


@control
def set_enqueue_first(request: WSGIRequest) -> HttpResponse:
    """Enables or disables the new music only mode based on the given value."""
    value, response = extract_value(request.POST)
    storage.put("enqueue_first", strtobool(value))
    return response


@control
def set_song_cooldown(request: WSGIRequest) -> HttpResponse:
    """Enables or disables the new music only mode based on the given value."""
    value, response = extract_value(request.POST)
    storage.put("song_cooldown", float(value))
    return response


@control
def set_max_download_size(request: WSGIRequest) -> HttpResponse:
    """Sets the maximum amount of MB that are allowed for a song that needs to be downloaded."""
    value, response = extract_value(request.POST)
    storage.put("max_download_size", float(value))
    return response


@control
def set_max_playlist_items(request: WSGIRequest) -> HttpResponse:
    """Sets the maximum number of songs that are downloaded from a playlist."""
    value, response = extract_value(request.POST)
    storage.put("max_playlist_items", int(value))
    return response


@control
def set_max_queue_length(request: WSGIRequest) -> HttpResponse:
    """Sets the maximum number of songs that are downloaded from a playlist."""
    value, response = extract_value(request.POST)
    storage.put("max_queue_length", int(value))
    return response


@control
def set_additional_keywords(request: WSGIRequest) -> HttpResponse:
    """Sets the keywords to filter out of results."""
    value, response = extract_value(request.POST)
    storage.put("additional_keywords", value)
    return response


@control
def set_forbidden_keywords(request: WSGIRequest) -> HttpResponse:
    """Sets the keywords to filter out of results."""
    value, response = extract_value(request.POST)
    storage.put("forbidden_keywords", value)
    return response


@control
def set_people_to_party(request: WSGIRequest) -> HttpResponse:
    """Sets the amount of active clients needed to enable partymode."""
    value, response = extract_value(request.POST)
    storage.put("people_to_party", int(value))
    return response


@control
def set_alarm_probability(request: WSGIRequest) -> HttpResponse:
    """Sets the probability with which an alarm is triggered after each song."""
    value, response = extract_value(request.POST)
    storage.put("alarm_probability", float(value))
    return response


@control
def set_buzzer_cooldown(request: WSGIRequest) -> HttpResponse:
    """Sets the minimum time that needs to pass between buzzer presses."""
    value, response = extract_value(request.POST)
    storage.put("buzzer_cooldown", float(value))
    return response


@control
def set_buzzer_success_probability(request: WSGIRequest) -> HttpResponse:
    """Sets the probability for the buzzer to play a success sound."""
    value, response = extract_value(request.POST)
    storage.put("buzzer_success_probability", float(value))
    return response


@control
def trigger_alarm(_request: WSGIRequest) -> None:
    """Manually triggers an alarm."""
    if playback.trigger_alarm():
        # because a state update is sent after every control (including this one)
        # a state update with alarm not being set would be sent
        # prevent this by manually setting this redis variable prematurely
        redis.put("alarm_playing", True)
