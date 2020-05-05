"""This module handles the suggestions when starting to
type into the input field on the musiq page."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Dict, Union, List

from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse

import core.musiq.song_utils as song_utils
from core.models import ArchivedPlaylist, ArchivedSong
from core.musiq.music_provider import SongProvider
from core.musiq.spotify import Spotify
from core.musiq.youtube import Youtube
from django.core.handlers.wsgi import WSGIRequest
from django.http.response import JsonResponse, HttpResponse

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

    def get_suggestions(self, request: WSGIRequest) -> JsonResponse:
        """Returns suggestions for a given query.
        Combines online and offline suggestions."""
        terms = request.GET["term"].split()
        suggest_playlist = request.GET["playlist"] == "true"

        results: List[Dict[str, Union[str, int]]] = []

        if self.musiq.base.settings.has_internet:
            if self.musiq.base.settings.spotify_enabled:
                spotify_suggestions = Spotify().get_search_suggestions(
                    " ".join(terms), suggest_playlist
                )
                spotify_suggestions = spotify_suggestions[:2]
                for suggestion, external_url in spotify_suggestions:
                    results.append(
                        {
                            "key": external_url,
                            "value": suggestion,
                            "type": "spotify-online",
                        }
                    )

            if self.musiq.base.settings.youtube_enabled:
                youtube_suggestions = Youtube().get_search_suggestions(" ".join(terms))
                # limit to the first three online suggestions
                youtube_suggestions = youtube_suggestions[:2]
                for suggestion in youtube_suggestions:
                    results.append(
                        {"key": -1, "value": suggestion, "type": "youtube-online"}
                    )

        # The following query is roughly equivalent to the following SQL code:
        # SELECT DISTINCT id, title, artist, counter
        # FROM core_archivedsong s LEFT JOIN core_archivedquery q ON q.song
        # WHERE forall term in terms: term in q.query or term in s.artist or term in s.title
        # ORDER BY -counter
        if suggest_playlist:
            remaining_playlists = ArchivedPlaylist.objects.prefetch_related("queries")
            # exclude radios from suggestions
            remaining_playlists = remaining_playlists.exclude(
                list_id__startswith="RD"
            ).exclude(list_id__contains="&list=RD")

            for term in terms:
                remaining_playlists = remaining_playlists.filter(
                    Q(title__icontains=term) | Q(queries__query__icontains=term)
                )

            playlist_suggestions = (
                remaining_playlists.values("id", "title", "counter")
                .distinct()
                .order_by("-counter")[:20]
            )

            for playlist in playlist_suggestions:
                archived_playlist = ArchivedPlaylist.objects.get(id=playlist["id"])
                result_dict: Dict[str, Union[str, int]] = {
                    "key": playlist["id"],
                    "value": playlist["title"],
                    "counter": playlist["counter"],
                    "type": song_utils.determine_playlist_type(archived_playlist),
                }
                results.append(result_dict)
        else:
            remaining_songs = ArchivedSong.objects.prefetch_related("queries")

            for term in terms:
                remaining_songs = remaining_songs.filter(
                    Q(title__icontains=term)
                    | Q(artist__icontains=term)
                    | Q(queries__query__icontains=term)
                )

            song_suggestions = (
                remaining_songs.values("id", "title", "url", "artist", "counter")
                .distinct()
                .order_by("-counter")[:20]
            )

            for song in song_suggestions:
                provider = SongProvider.create(self.musiq, external_url=song["url"])
                cached = provider.check_cached()
                # don't suggest local songs if they are not cached (=not at expected location)
                if not cached and provider.type == "local":
                    continue
                # don't suggest online songs when we don't have internet
                if not self.musiq.base.settings.has_internet and not cached:
                    continue
                # don't suggest spotify songs if we are not logged in
                if (
                    not self.musiq.base.settings.spotify_enabled
                    and provider.type == "spotify"
                ):
                    continue
                # don't suggest youtube songs if it was disabled
                if (
                    not self.musiq.base.settings.youtube_enabled
                    and provider.type == "youtube"
                ):
                    continue
                result_dict = {
                    "key": song["id"],
                    "value": song_utils.displayname(song["artist"], song["title"]),
                    "counter": song["counter"],
                    "type": provider.type,
                }
                results.append(result_dict)

        return JsonResponse(results, safe=False)
