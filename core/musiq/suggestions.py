"""This module handles the suggestions when starting to
type into the input field on the musiq page."""

from __future__ import annotations

import random
import threading
from typing import Dict, Union, List

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponseBadRequest
from django.http.response import JsonResponse, HttpResponse
from watson import search as watson

import core.musiq.song_utils as song_utils
import core.settings.storage as storage
from core import redis
from core.models import ArchivedPlaylist, ArchivedSong
from core.musiq.song_provider import SongProvider


def random_suggestion(request: WSGIRequest) -> HttpResponse:
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


def online_suggestions(request: WSGIRequest) -> JsonResponse:
    """Returns online suggestions for a given query."""
    query = request.GET["term"]
    suggest_playlist = request.GET["playlist"] == "true"

    if storage.get("new_music_only") and not suggest_playlist:
        return JsonResponse([], safe=False)

    results: List[Dict[str, Union[str, int]]] = []
    if storage.get("online_suggestions") and redis.get("has_internet"):
        threads = []
        results_lock = threading.Lock()

        def fetch_youtube() -> None:
            from core.musiq.youtube import Youtube

            youtube_suggestions = Youtube().get_search_suggestions(query)
            youtube_suggestions = youtube_suggestions[
                : storage.get("youtube_suggestions")
            ]
            with results_lock:
                for suggestion in youtube_suggestions:
                    results.append(
                        {"key": -1, "value": suggestion, "type": "youtube-online"}
                    )

        def fetch_spotify() -> None:
            from core.musiq.spotify import Spotify

            spotify_suggestions = Spotify().get_search_suggestions(
                query, suggest_playlist
            )
            spotify_suggestions = spotify_suggestions[
                : storage.get("spotify_suggestions")
            ]
            with results_lock:
                for suggestion, external_url in spotify_suggestions:
                    results.append(
                        {
                            "key": external_url,
                            "value": suggestion,
                            "type": "spotify-online",
                        }
                    )

        def fetch_soundcloud() -> None:
            from core.musiq.soundcloud import Soundcloud

            soundcloud_suggestions = Soundcloud().get_search_suggestions(query)
            soundcloud_suggestions = soundcloud_suggestions[
                : storage.get("soundcloud_suggestions")
            ]
            with results_lock:
                for suggestion in soundcloud_suggestions:
                    results.append(
                        {"key": -1, "value": suggestion, "type": "soundcloud-online"}
                    )

        def fetch_jamendo() -> None:
            from core.musiq.jamendo import Jamendo

            jamendo_suggestions = Jamendo().get_search_suggestions(query)
            jamendo_suggestions = jamendo_suggestions[
                : storage.get("jamendo_suggestions")
            ]
            with results_lock:
                for suggestion in jamendo_suggestions:
                    results.append(
                        {"key": -1, "value": suggestion, "type": "jamendo-online"}
                    )

        suggestion_fetchers = {
            "youtube": fetch_youtube,
            "spotify": fetch_spotify,
            "soundcloud": fetch_soundcloud,
            "jamendo": fetch_jamendo,
        }

        for platform in ["youtube", "spotify", "soundcloud", "jamendo"]:
            if (
                storage.get(f"{platform}_enabled")
                and storage.get(f"{platform}_suggestions") > 0
            ):
                thread = threading.Thread(target=suggestion_fetchers[platform])
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

    return JsonResponse(results, safe=False)


def offline_suggestions(request: WSGIRequest) -> JsonResponse:
    """Returns offline suggestions for a given query."""
    query = request.GET["term"]
    suggest_playlist = request.GET["playlist"] == "true"

    if storage.get("new_music_only") and not suggest_playlist:
        return JsonResponse([], safe=False)

    results = []

    if suggest_playlist:
        search_results = watson.search(query, models=(ArchivedPlaylist,))[
            : storage.get("number_of_suggestions")
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
            : storage.get("number_of_suggestions")
        ]

        for search_result in search_results:
            song_info = search_result.meta

            if song_utils.is_forbidden(song_info["artist"]) or song_utils.is_forbidden(
                song_info["title"]
            ):
                continue

            try:
                provider = SongProvider.create(external_url=song_info["url"])
            except NotImplementedError:
                # For this song a provider is necessary that is not available
                # e.g. the song was played before, but the provider was disabled
                continue
            cached = provider.check_cached()
            # don't suggest online songs when we don't have internet
            if not redis.get("has_internet") and not cached:
                continue
            if provider.type == "local":
                # don't suggest local songs if they are not cached (=not at expected location)
                if not cached:
                    continue
            else:
                # don't suggest songs if the respective platform is disabled
                if not storage.get(f"{provider.type}_enabled"):
                    continue
            result_dict = {
                "key": song_info["id"],
                "value": song_utils.displayname(
                    song_info["artist"], song_info["title"]
                ),
                "counter": search_result.object.counter,
                "type": provider.type,
            }
            # Add duration for songs where it is available (=cached songs)
            if cached:
                metadata = provider.get_metadata()
                result_dict["durationFormatted"] = song_utils.format_seconds(
                    metadata["duration"]
                )
            results.append(result_dict)
        # mark suggestions whose displayname is identical
        seen_values = {}
        for i, result in enumerate(results):
            if result["value"] in seen_values:
                result["confusable"] = True
                results[seen_values[result["value"]]]["confusable"] = True
            seen_values[result["value"]] = i

    return JsonResponse(results, safe=False)
