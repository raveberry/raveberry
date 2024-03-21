"""This module handles all controls that change the playback."""

from __future__ import annotations

import datetime
import subprocess
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

from core import models, redis, user_manager
from core.musiq import musiq, playback, player
from core.settings import storage
from core.util import extract_value

SEEK_DISTANCE = 10


def control(func: Callable) -> Callable:
    """A decorator for functions that control the playback.
    Every control changes the views state and returns an empty response.
    At least mod privilege is required during voting."""

    def _decorator(request: WSGIRequest) -> HttpResponse:
        if storage.get(
            "interactivity"
        ) != storage.Interactivity.full_control and not user_manager.has_controls(
            request.user
        ):
            return HttpResponseForbidden()
        response = func(request)
        musiq.update_state()
        if response is not None:
            return response
        return HttpResponse()

    return wraps(func)(_decorator)


def start() -> None:
    """Initializes this module by restoring the volume."""
    volume = storage.get("volume")
    _set_volume(volume)


@control
def restart(_request: WSGIRequest) -> None:
    """Restarts the current song from the beginning."""
    player.restart()
    try:
        current_song = models.CurrentSong.objects.get()
        current_song.created = timezone.now()
        current_song.save()
    except models.CurrentSong.DoesNotExist:
        pass


@control
def seek_backward(_request: WSGIRequest) -> None:
    """Jumps back in the current song."""
    player.seek_backward(SEEK_DISTANCE)
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
    player.play()
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
    storage.put("paused", False)
    redis.put("paused", False)


def _pause() -> None:
    player.pause()
    try:
        current_song = models.CurrentSong.objects.get()
        current_song.last_paused = timezone.now()
        current_song.save()
    except models.CurrentSong.DoesNotExist:
        pass
    storage.put("paused", True)
    redis.put("paused", True)


@control
def pause(_request: WSGIRequest) -> None:
    """Pauses the current song if it is playing.
    No-op if already paused."""
    _pause()


@control
def seek_forward(_request: WSGIRequest) -> None:
    """Jumps forward in the current song."""
    player.seek_forward(SEEK_DISTANCE)
    try:
        current_song = models.CurrentSong.objects.get()
        current_song.created -= datetime.timedelta(seconds=SEEK_DISTANCE)
        current_song.save()
    except models.CurrentSong.DoesNotExist:
        pass


def _skip() -> None:
    player.skip()
    redis.put("backup_playing", False)
    try:
        current_song = models.CurrentSong.objects.get()
        current_song.created = timezone.now() - datetime.timedelta(
            seconds=current_song.duration
        )
        current_song.save()
    except models.CurrentSong.DoesNotExist:
        pass


@control
def skip(_request: WSGIRequest) -> None:
    """Skips the current song and continues with the next one."""
    _skip()


@control
def set_shuffle(request: WSGIRequest) -> None:
    """Enables or disables shuffle depending on the given value.
    If enabled, a random song in the queue is chosen as the next one.
    If not, the first one is chosen."""
    enabled = request.POST.get("value") == "true"
    storage.put("shuffle", enabled)


@control
def set_repeat(request: WSGIRequest) -> None:
    """Enables or disables repeat depending on the given value.
    If enabled, a song is enqueued again after it finished playing."""
    enabled = request.POST.get("value") == "true"
    storage.put("repeat", enabled)


@control
def set_autoplay(request: WSGIRequest) -> None:
    """Enables or disables autoplay depending on the given value.
    If enabled and the current song is the last one,
    a new song is enqueued, based on the current one."""
    enabled = request.POST.get("value") == "true"
    storage.put("autoplay", enabled)
    playback.handle_autoplay()


def _set_volume(volume) -> None:
    try:
        # Try to set the volume via the pulse server.
        # This is faster and does not impact visualization
        subprocess.run(
            f"pactl set-sink-volume @DEFAULT_SINK@ {round(volume*100)}%".split(),
            env={"PULSE_SERVER": conf.PULSE_SERVER},
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        # pulse is not installed or there is no server running.
        # TODO: why does this hang with spotipy?
        # it can't change the volume on the phone, but it should simply raise an error which gets catched and then move on
        player.set_volume(volume)


@control
def set_volume(request: WSGIRequest) -> HttpResponse:
    """Sets the playback volume.
    value has to be a float between 0 and 1."""
    volume, response = extract_value(request.POST)
    _set_volume(float(volume))
    storage.put("volume", float(volume))
    return response


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
    with transaction.atomic():
        playback.queue.all().delete()
    return HttpResponse()


@control
def prioritize(request: WSGIRequest) -> HttpResponse:
    """Prioritizes song by making it the first one in the queue."""
    key_param = request.POST.get("key")
    if key_param is None:
        return HttpResponseBadRequest()
    key = int(key_param)
    playback.queue.prioritize(key)
    return HttpResponse()


@control
def remove(request: WSGIRequest) -> HttpResponse:
    """Removes a song identified by the given key from the queue."""
    key_param = request.POST.get("key")
    if key_param is None:
        return HttpResponseBadRequest()
    key = int(key_param)
    try:
        removed = playback.queue.remove(key)
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
    prev_key_param = request.POST.get("prev")
    cur_key_param = request.POST.get("element")
    next_key_param = request.POST.get("next")
    if not cur_key_param:
        return HttpResponseBadRequest()
    if not prev_key_param:
        prev_key = None
    else:
        prev_key = int(prev_key_param)
    cur_key = int(cur_key_param)
    if not next_key_param:
        next_key = None
    else:
        next_key = int(next_key_param)
    try:
        playback.queue.reorder(prev_key, cur_key, next_key)
    except ValueError:
        return HttpResponseBadRequest("request on old state")
    return HttpResponse()


@csrf_exempt
@user_manager.tracked
def vote(request: WSGIRequest) -> HttpResponse:
    """Modify the vote-count of the given song by the given amount.
    If a song receives too many downvotes, it is removed."""
    key_param = request.POST.get("key")
    amount_param = request.POST.get("amount")
    if key_param is None or amount_param is None:
        return HttpResponseBadRequest()
    key = int(key_param)
    amount = int(amount_param)
    if amount < -2 or amount > 2 or amount == 0:
        return HttpResponseBadRequest()

    if storage.get("ip_checking") and not user_manager.try_vote(
        user_manager.get_client_ip(request), key, amount
    ):
        return HttpResponseBadRequest("nice try")

    if storage.get("color_indication") != storage.Privileges.nobody:
        user_manager.register_vote(request, key, amount)

    models.CurrentSong.objects.filter(queue_key=key).update(votes=F("votes") + amount)
    try:
        current_song = models.CurrentSong.objects.get()
        if (
            current_song.queue_key == key
            and current_song.votes
            <= -storage.get(  # pylint: disable=invalid-unary-operand-type
                "downvotes_to_kick"
            )
        ):
            _skip()
    except models.CurrentSong.DoesNotExist:
        pass

    removed = playback.queue.vote(
        key,
        amount,
        -storage.get("downvotes_to_kick"),  # pylint: disable=invalid-unary-operand-type
    )
    # if we removed a song by voting, and it was added by autoplay,
    # we want it to be the new basis for autoplay
    if removed is not None:
        if not removed.manually_requested:
            playback.handle_autoplay(removed.external_url or removed.title)
        else:
            playback.handle_autoplay()
    musiq.update_state()
    return HttpResponse()
