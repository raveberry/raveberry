"""This module handles all controls that change the playback."""

from __future__ import annotations

import re
import subprocess
from functools import wraps
from typing import Callable, TYPE_CHECKING

from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseForbidden
from django.http.response import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

import core.models as models
from core.models import Setting

if TYPE_CHECKING:
    from core.musiq.musiq import Musiq
    from core.musiq.playback import Playback


def control(func: Callable) -> Callable:
    """A decorator for functions that control the playback.
    Every control changes the views state and returns an empty response."""

    def _decorator(
        self: "Controller", request: WSGIRequest, *args, **kwargs
    ) -> HttpResponse:
        # don't allow controls during alarm
        if self.playback.alarm_playing.is_set():
            return HttpResponseBadRequest()
        func(self, request, *args, **kwargs)
        self.musiq.update_state()
        return HttpResponse()

    return wraps(func)(_decorator)


def disabled_when_voting(func: Callable) -> Callable:
    """A decorator for controls that are disabled during voting.
    Only users with appropriate privileges are still able to perform this action."""

    def _decorator(
        self: "Controller", request: WSGIRequest, *args, **kwargs
    ) -> HttpResponse:
        if (
            self.musiq.base.settings.basic.voting_system
            and not self.musiq.base.user_manager.has_controls(request.user)
        ):
            return HttpResponseForbidden()
        func(self, request, *args, **kwargs)
        self.musiq.update_state()
        return HttpResponse()

    return wraps(func)(_decorator)


class Controller:
    """This class provides endpoints for all playback controls."""

    SEEK_DISTANCE = 10 * 1000

    def __init__(self, musiq: "Musiq") -> None:
        self.musiq = musiq
        self.playback: "Playback" = self.musiq.playback

        self.shuffle: bool = (
            self.musiq.base.settings.get_setting("shuffle", "False") == "True"
        )
        self.repeat: bool = self.musiq.base.settings.get_setting(
            "repeat", "False"
        ) == "True"
        self.autoplay: bool = (
            self.musiq.base.settings.get_setting("autoplay", "False") == "True"
        )

    def start(self) -> None:
        try:
            # Try to get the volume from the pulse server.
            active_sink = False
            volume = 100
            for line in subprocess.check_output(
                "pactl list sinks".split(),
                env={"PULSE_SERVER": "127.0.0.1"},
                universal_newlines=True,
            ).splitlines():
                if active_sink and "Volume:" in line:
                    match = re.search(r"(\d+)%", line)
                    if not match:
                        raise ValueError
                    volume = int(match.groups()[0])
                    break
                if "State: RUNNING" in line:
                    active_sink = True
            self.volume = volume / 100
        except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
            with self.playback.mopidy_command(important=True):
                # pulse is not installed or there is no server running.
                # get volume from mopidy
                self.volume = self.playback.player.mixer.get_volume() / 100

    @disabled_when_voting
    @control
    def restart(self, _request: WSGIRequest) -> None:
        """Restarts the current song from the beginning."""
        with self.playback.mopidy_command() as allowed:
            if allowed:
                self.playback.player.playback.seek(0)

    @disabled_when_voting
    @control
    def seek_backward(self, _request: WSGIRequest) -> None:
        """Jumps back in the current song."""
        with self.playback.mopidy_command() as allowed:
            if allowed:
                current_position = self.playback.player.playback.get_time_position()
                self.playback.player.playback.seek(
                    current_position - self.SEEK_DISTANCE
                )

    @disabled_when_voting
    @control
    def play(self, _request: WSGIRequest) -> None:
        """Resumes the current song if it is paused.
        No-op if already playing."""
        with self.playback.mopidy_command() as allowed:
            if allowed:
                self.playback.player.playback.play()

    @disabled_when_voting
    @control
    def pause(self, _request: WSGIRequest) -> None:
        """Pauses the current song if it is playing.
        No-op if already paused."""
        with self.playback.mopidy_command() as allowed:
            if allowed:
                self.playback.player.playback.pause()

    @disabled_when_voting
    @control
    def seek_forward(self, _request: WSGIRequest) -> None:
        """Jumps forward in the current song."""
        with self.playback.mopidy_command() as allowed:
            if allowed:
                current_position = self.playback.player.playback.get_time_position()
                self.playback.player.playback.seek(
                    current_position + self.SEEK_DISTANCE
                )

    @disabled_when_voting
    @control
    def skip(self, _request: WSGIRequest) -> None:
        """Skips the current song and continues with the next one."""
        with self.playback.mopidy_command() as allowed:
            if allowed:
                if self.playback.backup_playing.is_set():
                    self.playback.backup_playing.clear()
                self.playback.player.playback.next()

    @disabled_when_voting
    @control
    def set_shuffle(self, request: WSGIRequest) -> None:
        """Enables or disables shuffle depending on the given value.
        If enabled, a random song in the queue is chosen as the next one.
        If not, the first one is chosen."""
        enabled = request.POST.get("value") == "true"
        Setting.objects.filter(key="shuffle").update(value=enabled)
        self.shuffle = enabled

    @disabled_when_voting
    @control
    def set_repeat(self, request: WSGIRequest) -> None:
        """Enables or disables repeat depending on the given value.
        If enabled, a song is enqueued again after it finished playing."""
        enabled = request.POST.get("value") == "true"
        Setting.objects.filter(key="repeat").update(value=enabled)
        self.repeat = enabled

    @disabled_when_voting
    @control
    def set_autoplay(self, request: WSGIRequest) -> None:
        """Enables or disables autoplay depending on the given value.
        If enabled and the current song is the last one,
        a new song is enqueued, based on the current one."""
        enabled = request.POST.get("value") == "true"
        Setting.objects.filter(key="autoplay").update(value=enabled)
        self.autoplay = enabled
        self.playback.handle_autoplay()

    @disabled_when_voting
    @control
    def set_volume(self, request: WSGIRequest) -> None:
        """Sets the playback volume.
        value has to be a float between 0 and 1."""
        self.volume = float(request.POST.get("value"))  # type: ignore
        try:
            # Try to set the volume via the pulse server.
            # This is faster and does not impact visualization
            subprocess.run(
                f"pactl set-sink-volume @DEFAULT_SINK@ {round(self.volume*100)}%".split(),
                env={"PULSE_SERVER": "127.0.0.1"},
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            # pulse is not installed or there is no server running.
            # change mopidy's volume
            with self.playback.mopidy_command() as allowed:
                if allowed:
                    self.playback.player.mixer.set_volume(round(self.volume * 100))

    @disabled_when_voting
    @control
    def remove_all(self, request: WSGIRequest) -> HttpResponse:
        """Empties the queue. Only admin is permitted to do this."""
        if not self.musiq.base.user_manager.is_admin(request.user):
            return HttpResponseForbidden()
        with self.playback.mopidy_command() as allowed:
            if allowed:
                with transaction.atomic():
                    count = self.playback.queue.count()
                    self.playback.queue.all().delete()
                for _ in range(count):
                    self.playback.queue_semaphore.acquire(blocking=False)
        return HttpResponse()

    @disabled_when_voting
    @control
    def prioritize(self, request: WSGIRequest) -> HttpResponse:
        """Prioritizes song by making it the first one in the queue."""
        key = request.POST.get("key")
        if key is None:
            return HttpResponseBadRequest()
        ikey = int(key)
        self.playback.queue.prioritize(ikey)
        return HttpResponse()

    @disabled_when_voting
    @control
    def remove(self, request: WSGIRequest) -> HttpResponse:
        """Removes a song identified by the given key from the queue."""
        key = request.POST.get("key")
        if key is None:
            return HttpResponseBadRequest()
        ikey = int(key)
        try:
            removed = self.playback.queue.remove(ikey)
            self.playback.queue_semaphore.acquire(blocking=False)
            # if we removed a song and it was added by autoplay,
            # we want it to be the new basis for autoplay
            if not removed.manually_requested:
                self.playback.handle_autoplay(removed.external_url or removed.title)
            else:
                self.playback.handle_autoplay()
        except models.QueuedSong.DoesNotExist:
            return HttpResponseBadRequest("song does not exist")
        return HttpResponse()

    @disabled_when_voting
    @control
    def reorder(self, request: WSGIRequest) -> HttpResponse:
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
            self.playback.queue.reorder(iprev_key, icur_key, inext_key)
        except ValueError:
            return HttpResponseBadRequest("request on old state")
        return HttpResponse()

    @control
    @csrf_exempt
    def vote_up(self, request: WSGIRequest) -> HttpResponse:
        """Increases the vote-count of the given song by one."""
        key = request.POST.get("key")
        if key is None:
            return HttpResponseBadRequest()
        ikey = int(key)

        models.CurrentSong.objects.filter(queue_key=ikey).update(votes=F("votes") + 1)
        self.playback.queue.vote_up(ikey)
        return HttpResponse()

    @control
    @csrf_exempt
    def vote_down(self, request: WSGIRequest) -> HttpResponse:
        """Decreases the vote-count of the given song by one.
        If a song receives too many downvotes, it is removed."""
        key = request.POST.get("key")
        if key is None:
            return HttpResponseBadRequest()
        ikey = int(key)

        models.CurrentSong.objects.filter(queue_key=ikey).update(votes=F("votes") - 1)
        try:
            current_song = models.CurrentSong.objects.get()
            if (
                current_song.queue_key == ikey
                and current_song.votes
                <= -self.musiq.base.settings.basic.downvotes_to_kick
            ):
                with self.playback.mopidy_command() as allowed:
                    if allowed:
                        self.playback.player.playback.next()
        except models.CurrentSong.DoesNotExist:
            pass

        removed = self.playback.queue.vote_down(
            ikey, -self.musiq.base.settings.basic.downvotes_to_kick
        )
        # if we removed a song by voting, and it was added by autoplay,
        # we want it to be the new basis for autoplay
        if removed is not None:
            self.playback.queue_semaphore.acquire(blocking=False)
            if not removed.manually_requested:
                self.playback.handle_autoplay(removed.external_url or removed.title)
            else:
                self.playback.handle_autoplay()
        return HttpResponse()
