"""This module handles all basic settings."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from django.core.handlers.wsgi import WSGIRequest

from core.models import Setting
from core.settings.settings import Settings

if TYPE_CHECKING:
    from core.base import Base


class Basic:
    """This class is responsible for handling basic setting changes."""

    def __init__(self, base: "Base"):
        self.base = base

        self.voting_system = Settings.get_setting("voting_system", "False") == "True"
        self.new_music_only = Settings.get_setting("new_music_only", "False") == "True"
        self.logging_enabled = Settings.get_setting("logging_enabled", "True") == "True"
        self.online_suggestions = (
            Settings.get_setting("online_suggestions", "True") == "True"
        )
        self.number_of_suggestions = int(
            Settings.get_setting("number_of_suggestions", "20")
        )
        self.people_to_party = int(Settings.get_setting("people_to_party", "3"))
        self.alarm_probability = float(Settings.get_setting("alarm_probability", "0"))
        self.downvotes_to_kick = int(Settings.get_setting("downvotes_to_kick", "2"))
        self.max_download_size = int(Settings.get_setting("max_download_size", "10"))
        self.max_playlist_items = int(Settings.get_setting("max_playlist_items", "10"))
        self.additional_keywords = Settings.get_setting("additional_keywords", "")
        self.forbidden_keywords = Settings.get_setting("forbidden_keywords", "")
        self._check_internet()

    def _check_internet(self) -> None:
        response = subprocess.call(
            ["ping", "-c", "1", "-W", "3", "1.1.1.1"], stdout=subprocess.DEVNULL
        )
        if response == 0:
            self.has_internet = True
        else:
            self.has_internet = False

    @Settings.option
    def set_voting_system(self, request: WSGIRequest) -> None:
        """Enables or disables the voting system based on the given value."""
        enabled = request.POST.get("value") == "true"
        Setting.objects.filter(key="voting_system").update(value=enabled)
        self.voting_system = enabled

    @Settings.option
    def set_new_music_only(self, request: WSGIRequest) -> None:
        """Enables or disables the new music only mode based on the given value."""
        enabled = request.POST.get("value") == "true"
        Setting.objects.filter(key="new_music_only").update(value=enabled)
        self.new_music_only = enabled

    @Settings.option
    def set_logging_enabled(self, request: WSGIRequest) -> None:
        """Enables or disables logging of requests and play logs based on the given value."""
        enabled = request.POST.get("value") == "true"
        Setting.objects.filter(key="logging_enabled").update(value=enabled)
        self.logging_enabled = enabled

    @Settings.option
    def set_online_suggestions(self, request: WSGIRequest) -> None:
        """Enables or disables the voting system based on the given value."""
        enabled = request.POST.get("value") == "true"
        Setting.objects.filter(key="online_suggestions").update(value=enabled)
        self.online_suggestions = enabled

    @Settings.option
    def set_number_of_suggestions(self, request: WSGIRequest) -> None:
        """Enables or disables the voting system based on the given value."""
        value = int(request.POST.get("value"))  # type: ignore
        Setting.objects.filter(key="number_of_suggestions").update(value=value)
        self.number_of_suggestions = value

    @Settings.option
    def set_people_to_party(self, request: WSGIRequest) -> None:
        """Sets the amount of active clients needed to enable partymode."""
        value = int(request.POST.get("value"))  # type: ignore
        Setting.objects.filter(key="people_to_party").update(value=value)
        self.people_to_party = value

    @Settings.option
    def set_alarm_probability(self, request: WSGIRequest) -> None:
        """Sets the probability with which an alarm is triggered after each song."""
        value = float(request.POST.get("value"))  # type: ignore
        Setting.objects.filter(key="alarm_probability").update(value=value)
        self.alarm_probability = value

    @Settings.option
    def set_downvotes_to_kick(self, request: WSGIRequest) -> None:
        """Sets the number of downvotes that are needed to remove a song from the queue."""
        value = int(request.POST.get("value"))  # type: ignore
        Setting.objects.filter(key="downvotes_to_kick").update(value=value)
        self.downvotes_to_kick = value

    @Settings.option
    def set_max_download_size(self, request: WSGIRequest) -> None:
        """Sets the maximum amount of MB that are allowed for a song that needs to be downloaded."""
        value = int(request.POST.get("value"))  # type: ignore
        Setting.objects.filter(key="max_download_size").update(value=value)
        self.max_download_size = value

    @Settings.option
    def set_max_playlist_items(self, request: WSGIRequest) -> None:
        """Sets the maximum number of songs that are downloaded from a playlist."""
        value = int(request.POST.get("value"))  # type: ignore
        Setting.objects.filter(key="max_playlist_items").update(value=value)
        self.max_playlist_items = value

    @Settings.option
    def set_additional_keywords(self, request: WSGIRequest):
        """Sets the keywords to filter out of results."""
        value = request.POST.get("value")
        Setting.objects.filter(key="additional_keywords").update(value=value)
        self.additional_keywords = value

    @Settings.option
    def set_forbidden_keywords(self, request: WSGIRequest):
        """Sets the keywords to filter out of results."""
        value = request.POST.get("value")
        Setting.objects.filter(key="forbidden_keywords").update(value=value)
        self.forbidden_keywords = value

    @Settings.option
    def check_internet(self, _request: WSGIRequest) -> None:
        """Checks whether an internet connection exists and updates the internal state."""
        self._check_internet()

    @Settings.option
    def update_user_count(self, _request: WSGIRequest) -> None:
        """Force an update on the active user count."""
        self.base.user_manager.update_user_count()
