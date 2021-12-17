"""This module handles all basic settings."""

from __future__ import annotations

import subprocess

from django.core.handlers.wsgi import WSGIRequest

from core import user_manager, redis
from core.settings import storage
from core.settings.settings import control
from core.musiq import playback


def start() -> None:
    """Initializes this module. Checks whether internet is accessible."""
    _check_internet()


def _check_internet() -> None:
    response = subprocess.call(
        ["ping", "-c", "1", "-W", "3", "1.1.1.1"], stdout=subprocess.DEVNULL
    )
    if response == 0:
        redis.set("has_internet", True)
    else:
        redis.set("has_internet", False)


@control
def set_voting_enabled(request: WSGIRequest) -> None:
    """Enables or disables voting based on the given value."""
    enabled = request.POST.get("value") == "true"
    storage.set("voting_enabled", enabled)


@control
def set_ip_checking(request: WSGIRequest) -> None:
    """Enables or disables ip checking based on the given value."""
    enabled = request.POST.get("value") == "true"
    storage.set("ip_checking", enabled)


@control
def set_new_music_only(request: WSGIRequest) -> None:
    """Enables or disables the new music only mode based on the given value."""
    enabled = request.POST.get("value") == "true"
    storage.set("new_music_only", enabled)


@control
def set_logging_enabled(request: WSGIRequest) -> None:
    """Enables or disables logging of requests and play logs based on the given value."""
    enabled = request.POST.get("value") == "true"
    storage.set("logging_enabled", enabled)


@control
def set_hashtags_active(request: WSGIRequest) -> None:
    """Enables or disables logging of requests and play logs based on the given value."""
    enabled = request.POST.get("value") == "true"
    storage.set("hashtags_active", enabled)


@control
def set_embed_stream(request: WSGIRequest) -> None:
    """Enables or disables logging of requests and play logs based on the given value."""
    enabled = request.POST.get("value") == "true"
    storage.set("embed_stream", enabled)


@control
def set_dynamic_embedded_stream(request: WSGIRequest) -> None:
    """Enables or disables logging of requests and play logs based on the given value."""
    enabled = request.POST.get("value") == "true"
    storage.set("dynamic_embedded_stream", enabled)


@control
def set_online_suggestions(request: WSGIRequest) -> None:
    """Enables or disables online suggestions based on the given value."""
    enabled = request.POST.get("value") == "true"
    storage.set("online_suggestions", enabled)


@control
def set_number_of_suggestions(request: WSGIRequest) -> None:
    """Set the number of archived suggestions based on the given value."""
    value = int(request.POST.get("value"))  # type: ignore
    storage.set("number_of_suggestions", value)


@control
def set_people_to_party(request: WSGIRequest) -> None:
    """Sets the amount of active clients needed to enable partymode."""
    value = int(request.POST.get("value"))  # type: ignore
    storage.set("people_to_party", value)


@control
def set_alarm_probability(request: WSGIRequest) -> None:
    """Sets the probability with which an alarm is triggered after each song."""
    value = float(request.POST.get("value"))  # type: ignore
    storage.set("alarm_probability", value)


@control
def set_buzzer_cooldown(request: WSGIRequest) -> None:
    """Sets the minimum time that needs to pass between buzzer presses."""
    value = int(request.POST.get("value"))  # type: ignore
    storage.set("buzzer_cooldown", value)


@control
def trigger_alarm(_request: WSGIRequest) -> None:
    """Manually triggers an alarm."""
    playback.trigger_alarm()
    # because a state update is sent after every control (including this one)
    # a state update with alarm not being set would be sent
    # prevent this by manually setting this redis variable prematurely
    redis.set("alarm_playing", True)


@control
def set_downvotes_to_kick(request: WSGIRequest) -> None:
    """Sets the number of downvotes that are needed to remove a song from the queue."""
    value = int(request.POST.get("value"))  # type: ignore
    storage.set("downvotes_to_kick", value)


@control
def set_max_download_size(request: WSGIRequest) -> None:
    """Sets the maximum amount of MB that are allowed for a song that needs to be downloaded."""
    value = float(request.POST.get("value"))  # type: ignore
    storage.set("max_download_size", value)


@control
def set_max_playlist_items(request: WSGIRequest) -> None:
    """Sets the maximum number of songs that are downloaded from a playlist."""
    value = int(request.POST.get("value"))  # type: ignore
    storage.set("max_playlist_items", value)


@control
def set_max_queue_length(request: WSGIRequest) -> None:
    """Sets the maximum number of songs that are downloaded from a playlist."""
    value = int(request.POST.get("value"))  # type: ignore
    storage.set("max_queue_length", value)


@control
def set_additional_keywords(request: WSGIRequest):
    """Sets the keywords to filter out of results."""
    value = request.POST.get("value")
    storage.set("additional_keywords", value)


@control
def set_forbidden_keywords(request: WSGIRequest):
    """Sets the keywords to filter out of results."""
    value = request.POST.get("value")
    storage.set("forbidden_keywords", value)


@control
def check_internet(_request: WSGIRequest) -> None:
    """Checks whether an internet connection exists and updates the internal state."""
    _check_internet()


@control
def update_user_count(_request: WSGIRequest) -> None:
    """Force an update on the active user count."""
    user_manager.update_user_count()
