"""This module handles the suggestions when starting to
type into the input field on the musiq page."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Dict, Union, List

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponseBadRequest
from django.http.response import JsonResponse, HttpResponse
from watson import search as watson

import core.musiq.song_utils as song_utils
from core.models import ArchivedPlaylist, ArchivedSong
from core.musiq.song_provider import SongProvider
from core.musiq.soundcloud import Soundcloud
from core.musiq.spotify import Spotify
from core.musiq.youtube import Youtube

if TYPE_CHECKING:
    from core.musiq.musiq import Musiq


class Suggestions:
    """This class provides endpoints that serve suggestions."""

    def __init__(self, musiq: "Musiq") -> None:
        self.musiq = musiq

    @classmethod
    def random_suggestion(cls, request: WSGIRequest) -> HttpResponse:
        """This method returns a random suggestion from the database.
        Depending on the value of :param playlist:,
        either a previously pushed playlist or song is returned."""
        suggest_playlist = request.GET["playlist"] == "true"
        if not suggest_playlist:
            if ArchivedSong.objects.count() == 0:
                return HttpResponseBadRequest("No songs to suggest from")
            index = random.randint(0, ArchivedSong.objects.count() - 1)
            song = ArchivedSong.objects.all()[index]
            return JsonResponse({"suggestion": song.displayname(), "key": song.id})

        # exclude radios from suggestions
        remaining_playlists = (
            ArchivedPlaylist.objects.all()
            .exclude(list_id__startswith="RD")
            .exclude(list_id__contains="&list=RD")
        )
        if remaining_playlists.count() == 0:
            return HttpResponseBadRequest("No playlists to suggest from")
        index = random.randint(0, remaining_playlists.count() - 1)
        playlist = remaining_playlists.all()[index]
        return JsonResponse({"suggestion": playlist.title, "key": playlist.id})

    def _online_suggestions(
        self, query, suggest_playlist
    ) -> List[Dict[str, Union[str, int]]]:
        results: List[Dict[str, Union[str, int]]] = []
        if (
            self.musiq.base.settings.basic.online_suggestions
            and self.musiq.base.settings.basic.has_internet
        ):
            platform_settings = self.musiq.base.settings.platforms

            if (
                platform_settings.spotify_enabled
                and platform_settings.spotify_suggestions > 0
            ):
                spotify_suggestions = Spotify().get_search_suggestions(
                    query, suggest_playlist
                )
                spotify_suggestions = spotify_suggestions[
                    : platform_settings.spotify_suggestions
                ]
                for suggestion, external_url in spotify_suggestions:
                    results.append(
                        {
                            "key": external_url,
                            "value": suggestion,
                            "type": "spotify-online",
                        }
                    )

            if (
                platform_settings.soundcloud_enabled
                and platform_settings.soundcloud_suggestions > 0
            ):
                soundcloud_suggestions = Soundcloud().get_search_suggestions(query)
                soundcloud_suggestions = soundcloud_suggestions[
                    : platform_settings.soundcloud_suggestions
                ]
                for suggestion in soundcloud_suggestions:
                    results.append(
                        {"key": -1, "value": suggestion, "type": "soundcloud-online"}
                    )

            if (
                platform_settings.youtube_enabled
                and platform_settings.youtube_suggestions > 0
            ):
                youtube_suggestions = Youtube().get_search_suggestions(query)
                youtube_suggestions = youtube_suggestions[
                    : platform_settings.youtube_suggestions
                ]
                for suggestion in youtube_suggestions:
                    results.append(
                        {"key": -1, "value": suggestion, "type": "youtube-online"}
                    )
        return results

    def get_suggestions(self, request: WSGIRequest) -> JsonResponse:
        """Returns suggestions for a given query.
        Combines online and offline suggestions."""
        query = request.GET["term"]
        suggest_playlist = request.GET["playlist"] == "true"

        if self.musiq.base.settings.basic.new_music_only and not suggest_playlist:
            return JsonResponse([], safe=False)

        results = self._online_suggestions(query, suggest_playlist)
        basic_settings = self.musiq.base.settings.basic

        if suggest_playlist:
            search_results = watson.search(query, models=(ArchivedPlaylist,))[
                : basic_settings.number_of_suggestions
            ]

            for playlist in search_results:
                playlist_info = playlist.meta
                archived_playlist = ArchivedPlaylist.objects.get(id=playlist_info["id"])
                result_dict: Dict[str, Union[str, int]] = {
                    "key": playlist_info["id"],
                    "value": playlist_info["title"],
                    "counter": playlist.object.counter,
                    "type": song_utils.determine_playlist_type(archived_playlist),
                }
                results.append(result_dict)
        else:
            search_results = watson.search(query, models=(ArchivedSong,))[
                : basic_settings.number_of_suggestions
            ]

            for search_result in search_results:
                song_info = search_result.meta
                provider = SongProvider.create(
                    self.musiq, external_url=song_info["url"]
                )
                cached = provider.check_cached()
                # don't suggest local songs if they are not cached (=not at expected location)
                if not cached and provider.type == "local":
                    continue
                # don't suggest online songs when we don't have internet
                if not self.musiq.base.settings.basic.has_internet and not cached:
                    continue
                # don't suggest youtube songs if it was disabled
                if (
                    not self.musiq.base.settings.platforms.youtube_enabled
                    and provider.type == "youtube"
                ):
                    continue
                # don't suggest spotify songs if we are not logged in
                if (
                    not self.musiq.base.settings.platforms.spotify_enabled
                    and provider.type == "spotify"
                ):
                    continue
                # don't suggest soundcloud songs if we are not logged in
                if (
                    not self.musiq.base.settings.platforms.soundcloud_enabled
                    and provider.type == "soundcloud"
                ):
                    continue
                result_dict = {
                    "key": song_info["id"],
                    "value": song_utils.displayname(
                        song_info["artist"], song_info["title"]
                    ),
                    "counter": search_result.object.counter,
                    "type": provider.type,
                }
                results.append(result_dict)

        return JsonResponse(results, safe=False)
