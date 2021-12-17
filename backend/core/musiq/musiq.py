"""This module handles all requests concerning the addition of music to the queue."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Union, List, Tuple, cast, Type

from django.conf import settings as conf
from django.core.handlers.wsgi import WSGIRequest
from django.forms.models import model_to_dict
from django.http import HttpResponseBadRequest
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from django.utils import timezone

import core.musiq.song_utils as song_utils
import core.settings.storage as storage
from core import util, base, redis, user_manager
from core.models import CurrentSong
from core.models import QueuedSong
from core.musiq.localdrive import LocalSongProvider
from core.musiq.music_provider import MusicProvider, WrongUrlError, ProviderError
from core.musiq.song_provider import SongProvider
from core.musiq.playlist_provider import PlaylistProvider
from core.state_handler import send_state

queue = QueuedSong.objects


def start() -> None:
    import core.musiq.controller as controller
    import core.musiq.playback as playback

    controller.start()
    playback.start()


def get_alarm_metadata() -> "Metadata":
    return {
        "artist": "Raveberry",
        "title": "ALARM!",
        "duration": song_utils.get_metadata(
            os.path.join(conf.BASE_DIR, "config/sounds/alarm.m4a")
        )["duration"],
        "internal_url": "alarm",
        "external_url": "https://raveberry.party/alarm",
        "stream_url": None,
        "cached": True,
    }


def do_request_music(
    session_key: str,
    query: str,
    key: Optional[int],
    playlist: bool,
    platform: str,
    archive: bool = True,
    manually_requested: bool = True,
) -> Tuple[bool, str, Optional[int]]:
    """Performs the actual requesting of the music, not an endpoint.
    Enqueues the requested song or playlist into the queue, using appropriate providers.
    Returns a 3-tuple: successful, message, queue_key"""
    providers: List[MusicProvider] = []

    provider: MusicProvider
    music_provider_class: Union[Type[PlaylistProvider], Type[SongProvider]]
    local_provider_class: Type[MusicProvider]
    jamendo_provider_class: Type[MusicProvider]
    soundcloud_provider_class: Type[MusicProvider]
    spotify_provider_class: Type[MusicProvider]
    youtube_provider_class: Type[MusicProvider]

    if playlist:
        music_provider_class = PlaylistProvider
        local_provider_class = PlaylistProvider
        if storage.get("jamendo_enabled"):
            from core.musiq.jamendo import JamendoPlaylistProvider

            jamendo_provider_class = JamendoPlaylistProvider
        if storage.get("soundcloud_enabled"):
            from core.musiq.soundcloud import SoundcloudPlaylistProvider

            soundcloud_provider_class = SoundcloudPlaylistProvider
        if storage.get("spotify_enabled"):
            from core.musiq.spotify import SpotifyPlaylistProvider

            spotify_provider_class = SpotifyPlaylistProvider
        if storage.get("youtube_enabled"):
            from core.musiq.youtube import YoutubePlaylistProvider

            youtube_provider_class = YoutubePlaylistProvider
    else:
        music_provider_class = SongProvider
        local_provider_class = LocalSongProvider
        if storage.get("jamendo_enabled"):
            from core.musiq.jamendo import JamendoSongProvider

            jamendo_provider_class = JamendoSongProvider
        if storage.get("soundcloud_enabled"):
            from core.musiq.soundcloud import SoundcloudSongProvider

            soundcloud_provider_class = SoundcloudSongProvider
        if storage.get("spotify_enabled"):
            from core.musiq.spotify import SpotifySongProvider

            spotify_provider_class = SpotifySongProvider
        if storage.get("youtube_enabled"):
            from core.musiq.youtube import YoutubeSongProvider

            youtube_provider_class = YoutubeSongProvider

    if key is not None:
        # an archived entry was requested.
        # The key determines the Provider
        provider = music_provider_class.create(query, key)
        if provider is None:
            return False, "No provider found for requested key", None
        providers.append(provider)
    else:
        if platform == "local":
            # local music can only be searched explicitly
            providers.append(local_provider_class(query, key))
        if storage.get("soundcloud_enabled"):
            try:
                soundcloud_provider = soundcloud_provider_class(query, key)
                if platform == "soundcloud":
                    providers.insert(0, soundcloud_provider)
                else:
                    providers.append(soundcloud_provider)
            except WrongUrlError:
                pass
        if storage.get("spotify_enabled"):
            try:
                spotify_provider = spotify_provider_class(query, key)
                if platform == "spotify":
                    providers.insert(0, spotify_provider)
                else:
                    providers.append(spotify_provider)
            except WrongUrlError:
                pass
        if storage.get("jamendo_enabled"):
            try:
                jamendo_provider = jamendo_provider_class(query, key)
                if platform == "jamendo":
                    providers.insert(0, jamendo_provider)
                else:
                    providers.append(jamendo_provider)
            except WrongUrlError:
                pass
        if storage.get("youtube_enabled"):
            try:
                youtube_provider = youtube_provider_class(query, key)
                if platform == "youtube":
                    providers.insert(0, youtube_provider)
                else:
                    providers.append(youtube_provider)
            except WrongUrlError:
                pass

    if not providers:
        return False, "No backend configured to handle your request.", None

    fallback = False
    for i, provider in enumerate(providers):
        try:
            provider.request(
                session_key, archive=archive, manually_requested=manually_requested
            )
            # the current provider could provide the song, don't try the other ones
            break
        except ProviderError:
            # this provider cannot provide this song, use the next provider
            # if this was the last provider, show its error
            # in new music only mode, do not allow fallbacks
            if storage.get("new_music_only") or i == len(providers) - 1:
                return False, provider.error, None
            fallback = True
    message = provider.ok_message
    queue_key = None
    if not playlist:
        queued_song = cast(SongProvider, provider).queued_song
        if not queued_song:
            logging.error(
                "no placeholder was created for query '%s' and key '%s'", query, key
            )
            return False, "No placeholder was created", None
        queue_key = queued_song.id
    if fallback:
        message += " (used fallback)"
    return True, message, queue_key


# accessed by the discord bot
@csrf_exempt
@user_manager.tracked
def request_music(request: WSGIRequest) -> HttpResponse:
    """Endpoint to request music. Calls internal function."""
    key = request.POST.get("key")
    query = request.POST.get("query")
    playlist = request.POST.get("playlist") == "true"
    platform = request.POST.get("platform")

    if query is None or not platform:
        return HttpResponseBadRequest(
            "query, playlist and platform have to be specified."
        )
    ikey = None
    if key:
        ikey = int(key)

    successful, message, queue_key = do_request_music(
        request.session.session_key, query, ikey, playlist, platform
    )
    if not successful:
        return HttpResponseBadRequest(message)

    if storage.get("ip_checking") and not playlist:
        user_manager.try_vote(user_manager.get_client_ip(request), queue_key, 1)

    return JsonResponse({"message": message, "key": queue_key})


@user_manager.tracked
def request_radio(request: WSGIRequest) -> HttpResponse:
    """Endpoint to request radio for the current song."""
    try:
        current_song = CurrentSong.objects.get()
    except CurrentSong.DoesNotExist:
        return HttpResponseBadRequest("Need a song to play the radio")
    provider = SongProvider.create(external_url=current_song.external_url)
    return provider.request_radio(request.session.session_key)


def index(request: WSGIRequest) -> HttpResponse:
    """Renders the /musiq page."""
    from core import urls

    context = base.context(request)
    context["urls"] = urls.musiq_paths
    context["additional_keywords"] = storage.get("additional_keywords")
    context["forbidden_keywords"] = storage.get("forbidden_keywords")
    context["embed_stream"] = storage.get("embed_stream")
    context["dynamic_embedded_stream"] = storage.get("dynamic_embedded_stream")
    for platform in ["youtube", "spotify", "soundcloud", "jamendo"]:
        if storage.get("online_suggestions") and storage.get(f"{platform}_enabled"):
            suggestion_count = storage.get(f"{platform}_suggestions")
        else:
            suggestion_count = 0
        context[f"{platform}_suggestions"] = suggestion_count
    return render(request, "musiq.html", context)


def state_dict() -> Dict[str, Any]:
    state = base.state_dict()

    musiq_state = {}

    musiq_state["paused"] = storage.get("paused")
    musiq_state["shuffle"] = storage.get("shuffle")
    musiq_state["repeat"] = storage.get("repeat")
    musiq_state["autoplay"] = storage.get("autoplay")
    musiq_state["volume"] = storage.get("volume")

    try:
        current_song = CurrentSong.objects.get()
        current_song_dict = model_to_dict(current_song)
        current_song_dict = util.camelize(current_song_dict)
        current_song_dict["durationFormatted"] = song_utils.format_seconds(
            current_song_dict["duration"]
        )
        musiq_state["currentSong"] = current_song_dict

        paused = storage.get("paused")
        if paused:
            progress = (current_song.last_paused - current_song.created).total_seconds()
        else:
            progress = (timezone.now() - current_song.created).total_seconds()
        progress /= current_song.duration
        musiq_state["progress"] = progress * 100
    except CurrentSong.DoesNotExist:
        musiq_state["currentSong"] = None
        musiq_state["paused"] = True
        musiq_state["progress"] = 0

    song_queue = []
    total_time = 0
    all_songs = queue.all()
    if storage.get("voting_enabled"):
        all_songs = all_songs.order_by("-votes", "index")
    for song in all_songs:
        song_dict = model_to_dict(song)
        song_dict = util.camelize(song_dict)
        song_dict["durationFormatted"] = song_utils.format_seconds(
            song_dict["duration"]
        )
        song_queue.append(song_dict)
        if song_dict["duration"] < 0:
            # skip duration of placeholders
            continue
        total_time += song_dict["duration"]
    musiq_state["totalTimeFormatted"] = song_utils.format_seconds(total_time)
    musiq_state["songQueue"] = song_queue

    if state["alarm"]:
        musiq_state["currentSong"] = {
            "queueKey": -1,
            "manuallyRequested": False,
            "votes": 0,
            "created": "",
            **util.camelize(get_alarm_metadata()),
        }
        musiq_state["progress"] = 0
        musiq_state["paused"] = False
    elif redis.get("backup_playing"):
        musiq_state["currentSong"] = {
            "queueKey": -1,
            "manuallyRequested": False,
            "votes": 0,
            "internalUrl": "backup_stream",
            "externalUrl": storage.get("backup_stream"),
            "artist": "",
            "title": "Backup Stream",
            "duration": 60 * 60 * 24,
            "created": "",
        }
        musiq_state["paused"] = False

    state["musiq"] = musiq_state
    return state


def update_state() -> None:
    """Sends an update event to all connected clients."""
    send_state(state_dict())
