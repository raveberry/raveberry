"""This module handles all requests concerning the addition of music to the queue."""

from __future__ import annotations

import ast
import importlib
import logging
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from django.conf import settings as conf
from django.core.handlers.wsgi import WSGIRequest
from django.forms.models import model_to_dict
from django.http import HttpResponseBadRequest
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core import base, redis, user_manager, util
from core.models import CurrentSong, QueuedSong
from core.musiq import controller, playback, song_utils
from core.musiq.music_provider import MusicProvider, ProviderError, WrongUrlError
from core.musiq.playlist_provider import PlaylistProvider
from core.musiq.song_provider import SongProvider
from core.settings import storage
from core.state_handler import send_state
from core.settings.storage import PlatformEnabled, PlatformSuggestions

queue = QueuedSong.objects

if TYPE_CHECKING:
    from core.musiq.song_utils import Metadata


def start() -> None:
    """Initializes the required modules."""

    controller.start()
    playback.start()


def get_alarm_metadata() -> "Metadata":
    """Returns a metadata object for the alarm. The duration is dynamically determined."""
    return {
        "artist": "Raveberry",
        "title": "ALARM!",
        "duration": song_utils.get_metadata(
            os.path.join(conf.BASE_DIR, "resources/sounds/alarm.m4a")
        )["duration"],
        "internal_url": "alarm",
        "external_url": "https://raveberry.party/alarm",
        "stream_url": None,
        "cached": True,
    }


def enabled_platforms_by_priority() -> List[str]:
    """Returns a list of all available platforms, ordered by priority."""
    # local music can only be searched explicitly by key and thus is last
    return [
        platform
        for platform in ["spotify", "youtube", "soundcloud", "jamendo", "local"]
        if storage.get(cast(PlatformEnabled, f"{platform}_enabled"))
    ]


def get_providers(
    query: str,
    key: Optional[int] = None,
    playlist: bool = False,
    preferred_platform: Optional[str] = None,
) -> List[MusicProvider]:
    """Returns a list of all available providers for the given query, ordered by priority.
    If a preferred platform is given, that provider will be first."""

    if key is not None:
        # an archived entry was requested.
        # The key determines the Provider
        provider: MusicProvider
        try:
            if playlist:
                provider = PlaylistProvider.create(query, key)
            else:
                provider = SongProvider.create(query, key)
            return [provider]
        except ProviderError:
            # No provider is available for the requested key
            # This might be because the platform of that archived song is not available anymore
            # -> treat the request like a search query
            # delete the key so the archived song for the different platform is disregarded
            key = None

    providers: List[MusicProvider] = []
    for platform in enabled_platforms_by_priority():
        module = importlib.import_module(f"core.musiq.{platform}")
        if playlist:
            provider_class = getattr(module, f"{platform.title()}PlaylistProvider")
        else:
            provider_class = getattr(module, f"{platform.title()}SongProvider")
        try:
            provider = provider_class(query, key)
            if platform == preferred_platform:
                providers.insert(0, provider)
            else:
                providers.append(provider)
        except WrongUrlError:
            pass

    if not providers:
        raise ProviderError("No backend configured to handle your request.")

    return providers


def try_providers(session_key: str, providers: List[MusicProvider]) -> MusicProvider:
    """Goes through every given provider and tries to request its music.
    Returns the first provider that was successful with an empty error.
    If unsuccessful, return the last provider."""

    fallback = False
    last_provider = providers[-1]
    provider = providers[0]
    for provider in providers:
        try:
            provider.request(session_key)
            # the current provider could provide the song, don't try the other ones
            break
        except ProviderError:
            # this provider cannot provide this song, use the next provider
            # if this was the last provider, show its error
            # in new music only mode, do not allow fallbacks
            if storage.get("new_music_only") or provider == last_provider:
                return provider
            fallback = True
    provider.error = ""
    if fallback:
        provider.ok_message += " (used fallback)"
    return provider


# accessed by the discord bot
@csrf_exempt
@user_manager.tracked
def request_music(request: WSGIRequest) -> HttpResponse:
    """Endpoint to request music."""
    key_param = request.POST.get("key")
    query = request.POST.get("query")
    playlist = request.POST.get("playlist") == "true"
    platform = request.POST.get("platform")

    if query is None:
        return HttpResponseBadRequest("No query given")
    key = None
    if key_param:
        key = int(key_param)

    try:
        providers = get_providers(query, key, playlist, platform)
    except ProviderError as error:
        return HttpResponseBadRequest(str(error))

    provider = try_providers(request.session.session_key, providers)
    if provider.error:
        return HttpResponseBadRequest(provider.error)

    queue_key = None
    if not playlist:
        assert isinstance(provider, SongProvider)
        queued_song = provider.queued_song
        if not queued_song:
            logging.error(
                "no placeholder was created for query '%s' and key '%s'", query, key
            )
            return HttpResponseBadRequest("No placeholder was created")
        queue_key = queued_song.id

        if storage.get("ip_checking"):
            assert queue_key
            user_manager.try_vote(user_manager.get_client_ip(request), queue_key, 1)

        if storage.get("color_indication") != storage.Privileges.nobody:
            user_manager.register_song(request, queue_key)
            user_manager.register_vote(request, queue_key, 1)

    return JsonResponse({"message": provider.ok_message, "key": queue_key})


@user_manager.tracked
def request_radio(request: WSGIRequest) -> HttpResponse:
    """Endpoint to request radio for the current song."""
    try:
        current_song = CurrentSong.objects.get()
    except CurrentSong.DoesNotExist:
        return HttpResponseBadRequest("Need a song to play the radio")
    provider = SongProvider.create(external_url=current_song.external_url)
    return provider.request_radio(request.session.session_key)


@user_manager.tracked
def index(request: WSGIRequest) -> HttpResponse:
    """Renders the /musiq page."""
    from core import urls

    context = base.context(request)
    context["urls"] = urls.musiq_paths
    context["additional_keywords"] = storage.get("additional_keywords")
    context["forbidden_keywords"] = storage.get("forbidden_keywords")
    context["client_streaming"] = storage.get("output") == "client"
    context["show_stream"] = storage.get("output") in ["client", "icecast"] and (
        not storage.get("privileged_stream") or context["controls_enabled"]
    )
    for platform in ["youtube", "spotify", "soundcloud", "jamendo"]:
        if (
            storage.get("online_suggestions")
            and not storage.get("new_music_only")
            and storage.get(cast(PlatformEnabled, f"{platform}_enabled"))
        ):
            suggestion_count = storage.get(
                cast(PlatformSuggestions, f"{platform}_suggestions")
            )
        else:
            suggestion_count = 0
        context[f"{platform}_suggestions"] = suggestion_count
    return render(request, "musiq.html", context)


def _add_color_indication(engagement, song_dict) -> None:
    requested_by = None
    votes = {}
    if engagement is not None:
        requested_by, votes = ast.literal_eval(engagement)
    song_dict["requestedBy"] = user_manager.color_of(requested_by)
    song_dict["requesterVote"] = votes.get(requested_by, 0)
    song_dict["upvotes"] = []
    song_dict["downvotes"] = []
    for session_key, amount in votes.items():
        if session_key == requested_by:
            continue
        color = user_manager.color_of(session_key)
        if amount > 0:
            song_dict["upvotes"].append(color)
        else:
            song_dict["downvotes"].append(color)


def state_dict() -> Dict[str, Any]:
    """Extends the base state with musiq-specific information and returns it."""
    state = base.state_dict()

    musiq_state: Dict[str, Any] = {}

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
        if storage.get("color_indication") != storage.Privileges.nobody:
            engagement = redis.connection.get(f"engagement-{current_song.queue_key}")
            _add_color_indication(engagement, current_song_dict)
        musiq_state["currentSong"] = current_song_dict

        paused = storage.get("paused")
        if paused:
            progress = (current_song.last_paused - current_song.created).total_seconds()
        else:
            progress = (timezone.now() - current_song.created).total_seconds()
        try:
            progress /= current_song.duration
        except ZeroDivisionError:
            progress = 1
        musiq_state["progress"] = progress * 100
    except CurrentSong.DoesNotExist:
        musiq_state["currentSong"] = None
        musiq_state["paused"] = True
        musiq_state["progress"] = 0

    song_queue = []
    total_time = 0
    all_songs = queue.all()
    if storage.get("interactivity") in [
        storage.Interactivity.upvotes_only,
        storage.Interactivity.full_voting,
    ]:
        all_songs = all_songs.order_by("-votes", "index")
    for song in all_songs:
        song_dict = model_to_dict(song)
        song_dict = util.camelize(song_dict)
        song_dict["durationFormatted"] = song_utils.format_seconds(
            song_dict["duration"]
        )
        if storage.get("color_indication"):
            engagement = redis.connection.get(f"engagement-{song.id}")
            _add_color_indication(engagement, song_dict)
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
            # https://github.com/python/mypy/issues/4976
            **util.camelize(cast(Dict[Any, Any], get_alarm_metadata())),
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
