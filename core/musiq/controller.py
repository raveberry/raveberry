"""This module handles all controls that change the playback."""

from __future__ import annotations

import subprocess
import datetime
from functools import wraps
from typing import Callable

from django.conf import settings as conf
from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseForbidden
from django.http.response import HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from mopidyapi import MopidyAPI

import core.models as models
from core import user_manager, redis
from core.musiq import playback, musiq
from core.settings import storage

player: MopidyAPI = None


def control(func: Callable) -> Callable:
    """A decorator for functions that control the playback.
    Every control changes the views state and returns an empty response.
    At least mod privilege is required during voting."""

    def _decorator(request: WSGIRequest) -> HttpResponse:
        if storage.get("voting_enabled") and not user_manager.has_controls(
            request.user
        ):
            return HttpResponseForbidden()
        response = func(request)
        musiq.update_state()
        if response is not None:
            return response
        return HttpResponse()

    return wraps(func)(_decorator)


SEEK_DISTANCE = 10


def start() -> None:
    """Initializes this module by restoring the volume."""
    global player
    player = MopidyAPI(host=conf.MOPIDY_HOST)
    volume = storage.get("volume")
    _set_volume(volume)


@control
def restart(_request: WSGIRequest) -> None:
    """Restarts the current song from the beginning."""
    with playback.mopidy_command() as allowed:
        if allowed:
            player.playback.seek(0)
    try:
        current_song = models.CurrentSong.objects.get()
        current_song.created = timezone.now()
        current_song.save()
    except models.CurrentSong.DoesNotExist:
        pass


@control
def seek_backward(_request: WSGIRequest) -> None:
    """Jumps back in the current song."""
    with playback.mopidy_command() as allowed:
        if allowed:
            current_position = player.playback.get_time_position()
            player.playback.seek(current_position - SEEK_DISTANCE * 1000)
    try:
        current_song = models.CurrentSong.objects.get()
        now = timezone.now()
        current_song.created += datetime.timedelta(seconds=SEEK_DISTANCE)
        current_song.created = min(current_song.created, now)
        current_song.save()
    except models.CurrentSong.DoesNotExist:
        pass


@control
def play(_request: WSGIRequest) -> None:
    """Resumes the current song if it is paused.
    No-op if already playing."""
    with playback.mopidy_command() as allowed:
        if allowed:
            player.playback.play()
    try:
        # move the creation timestamp into the future for the duration of the pause
        # this ensures that the progress calculation (starting from created) is correct
        current_song = models.CurrentSong.objects.get()
        now = timezone.now()
        pause_duration = (now - current_song.last_paused).total_seconds()
        current_song.created += datetime.timedelta(seconds=pause_duration)
        current_song.created = min(current_song.created, now)
        current_song.save()
    except models.CurrentSong.DoesNotExist:
        pass
    storage.set("paused", False)


@control
def pause(_request: WSGIRequest) -> None:
    """Pauses the current song if it is playing.
    No-op if already paused."""
    with playback.mopidy_command() as allowed:
        if allowed:
            player.playback.pause()
    try:
        current_song = models.CurrentSong.objects.get()
        current_song.last_paused = timezone.now()
        current_song.save()
    except models.CurrentSong.DoesNotExist:
        pass
    storage.set("paused", True)


@control
def seek_forward(_request: WSGIRequest) -> None:
    """Jumps forward in the current song."""
    with playback.mopidy_command() as allowed:
        if allowed:
            current_position = player.playback.get_time_position()
            player.playback.seek(current_position + SEEK_DISTANCE * 1000)
    try:
        current_song = models.CurrentSong.objects.get()
        current_song.created -= datetime.timedelta(seconds=SEEK_DISTANCE)
        current_song.save()
    except models.CurrentSong.DoesNotExist:
        pass


@control
def skip(_request: WSGIRequest) -> None:
    """Skips the current song and continues with the next one."""
    with playback.mopidy_command() as allowed:
        if allowed:
            redis.set("backup_playing", False)
            player.playback.next()


@control
def set_shuffle(request: WSGIRequest) -> None:
    """Enables or disables shuffle depending on the given value.
    If enabled, a random song in the queue is chosen as the next one.
    If not, the first one is chosen."""
    enabled = request.POST.get("value") == "true"
    storage.set("shuffle", enabled)


@control
def set_repeat(request: WSGIRequest) -> None:
    """Enables or disables repeat depending on the given value.
    If enabled, a song is enqueued again after it finished playing."""
    enabled = request.POST.get("value") == "true"
    storage.set("repeat", enabled)


@control
def set_autoplay(request: WSGIRequest) -> None:
    """Enables or disables autoplay depending on the given value.
    If enabled and the current song is the last one,
    a new song is enqueued, based on the current one."""
    enabled = request.POST.get("value") == "true"
    storage.set("autoplay", enabled)
    playback.handle_autoplay()


def _set_volume(volume) -> None:
    try:
        # Try to set the volume via the pulse server.
        # This is faster and does not impact visualization
        subprocess.run(
            f"pactl set-sink-volume @DEFAULT_SINK@ {round(volume*100)}%".split(),
            env={"PULSE_SERVER": "127.0.0.1"},
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        # pulse is not installed or there is no server running.
        # change mopidy's volume
        with playback.mopidy_command() as allowed:
            if allowed:
                player.mixer.set_volume(round(volume * 100))


@control
def set_volume(request: WSGIRequest) -> None:
    """Sets the playback volume.
    value has to be a float between 0 and 1."""
    volume = float(request.POST.get("value"))  # type: ignore
    _set_volume(volume)
    storage.set("volume", volume)


@control
def shuffle_all(request: WSGIRequest) -> HttpResponse:
    """Shuffles the queue. Only admin is permitted to do this."""
    if not user_manager.is_admin(request.user):
        return HttpResponseForbidden()
    playback.queue.shuffle()
    return HttpResponse()


@control
def remove_all(request: WSGIRequest) -> HttpResponse:
    """Empties the queue. Only admin is permitted to do this."""
    if not user_manager.is_admin(request.user):
        return HttpResponseForbidden()
    with playback.mopidy_command() as allowed:
        if allowed:
            with transaction.atomic():
                playback.queue.all().delete()
    return HttpResponse()


@control
def prioritize(request: WSGIRequest) -> HttpResponse:
    """Prioritizes song by making it the first one in the queue."""
    key = request.POST.get("key")
    if key is None:
        return HttpResponseBadRequest()
    ikey = int(key)
    playback.queue.prioritize(ikey)
    return HttpResponse()


@control
def remove(request: WSGIRequest) -> HttpResponse:
    """Removes a song identified by the given key from the queue."""
    key = request.POST.get("key")
    if key is None:
        return HttpResponseBadRequest()
    ikey = int(key)
    try:
        removed = playback.queue.remove(ikey)
        # if we removed a song and it was added by autoplay,
        # we want it to be the new basis for autoplay
        if not removed.manually_requested:
            playback.handle_autoplay(removed.external_url or removed.title)
        else:
            playback.handle_autoplay()
    except models.QueuedSong.DoesNotExist:
        return HttpResponseBadRequest("song does not exist")
    return HttpResponse()


@control
def reorder(request: WSGIRequest) -> HttpResponse:
    """Reorders the queue.
    The song specified by element is inserted between prev and next."""
    prev_key = request.POST.get("prev")
    cur_key = request.POST.get("element")
    next_key = request.POST.get("next")
    if not cur_key:
        return HttpResponseBadRequest()
    if not prev_key:
        iprev_key = None
    else:
        iprev_key = int(prev_key)
    icur_key = int(cur_key)
    if not next_key:
        inext_key = None
    else:
        inext_key = int(next_key)
    try:
        playback.queue.reorder(iprev_key, icur_key, inext_key)
    except ValueError:
        return HttpResponseBadRequest("request on old state")
    return HttpResponse()


@csrf_exempt
def vote(request: WSGIRequest) -> HttpResponse:
    """Modify the vote-count of the given song by the given amount.
    If a song receives too many downvotes, it is removed."""
    key = request.POST.get("key")
    amount = request.POST.get("amount")
    if key is None or amount is None:
        return HttpResponseBadRequest()
    ikey = int(key)
    amount = int(amount)
    if amount < -2 or amount > 2:
        return HttpResponseBadRequest()

    if storage.get("ip_checking") and not user_manager.try_vote(
        user_manager.get_client_ip(request), ikey, amount
    ):
        return HttpResponseBadRequest("nice try")

    models.CurrentSong.objects.filter(queue_key=ikey).update(votes=F("votes") + amount)
    try:
        current_song = models.CurrentSong.objects.get()
        if current_song.queue_key == ikey and current_song.votes <= -storage.get(
            "downvotes_to_kick"
        ):
            with playback.mopidy_command() as allowed:
                if allowed:
                    player.playback.next()
    except models.CurrentSong.DoesNotExist:
        pass

    removed = playback.queue.vote(ikey, amount, -storage.get("downvotes_to_kick"))
    # if we removed a song by voting, and it was added by autoplay,
    # we want it to be the new basis for autoplay
    if removed is not None:
        if not removed.manually_requested:
            playback.handle_autoplay(removed.external_url or removed.title)
        else:
            playback.handle_autoplay()
    musiq.update_state()
    return HttpResponse()
