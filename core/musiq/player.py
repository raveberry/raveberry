"""This module contains the player, handling playback of music."""

from __future__ import annotations

import logging
import os
import random
import re
import subprocess
import time
from contextlib import contextmanager
from functools import wraps
from threading import Event
from threading import Lock
from threading import Semaphore

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.utils import timezone
from mopidyapi.client import MopidyAPI
from mopidyapi.exceptions import MopidyError
import requests

import core.models as models
from core.models import Setting
from core.musiq.music_provider import SongProvider
from core.util import background_thread
from django.core.handlers.wsgi import WSGIRequest
from django.http.response import HttpResponse, HttpResponseBadRequest
from typing import (
    Callable,
    Iterator,
    Optional,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from core.musiq.musiq import Musiq


def control(func: Callable) -> Callable:
    """A decorator for functions that control the playback.
    Every control changes the views state and returns an empty response."""

    def _decorator(
        self: "Player", request: WSGIRequest, *args, **kwargs
    ) -> HttpResponse:
        # don't allow controls during alarm
        if self.alarm_playing.is_set():
            return HttpResponseBadRequest()
        func(self, request, *args, **kwargs)
        self.musiq.update_state()
        return HttpResponse()

    return wraps(func)(_decorator)


def disabled_when_voting(func: Callable) -> Callable:
    """A decorator for controls that are disabled during voting.
    Only users with appropriate privileges are still able to perform this action."""

    def _decorator(
        self: "Player", request: WSGIRequest, *args, **kwargs
    ) -> HttpResponse:
        if (
            self.musiq.base.settings.voting_system
            and not self.musiq.base.user_manager.has_controls(request.user)
        ):
            return HttpResponseForbidden()
        func(self, request, *args, **kwargs)
        self.musiq.update_state()
        return HttpResponse()

    return wraps(func)(_decorator)


class Player:
    """This class handles music playback and provides endpoints to control it."""

    # this has to be a class variable
    # so the manager of the queue can access it without a player object
    queue_semaphore: Semaphore = None  # type: ignore

    SEEK_DISTANCE = 10 * 1000

    def __init__(self, musiq: "Musiq") -> None:
        self.musiq = musiq

        self.shuffle = (
            self.musiq.base.settings.get_setting("shuffle", "False") == "True"
        )
        self.repeat = self.musiq.base.settings.get_setting("repeat", "False") == "True"
        self.autoplay = (
            self.musiq.base.settings.get_setting("autoplay", "False") == "True"
        )

        self.queue = models.QueuedSong.objects
        Player.queue_semaphore = Semaphore(self.queue.count())
        self.alarm_playing: Event = Event()
        self.running = True

        self.player: MopidyAPI = MopidyAPI(host=settings.MOPIDY_HOST)
        self.player_lock = Lock()
        with self.mopidy_command(important=True):
            self.player.playback.stop()
            self.player.tracklist.clear()
            # make songs disappear from tracklist after being played
            self.player.tracklist.set_consume(True)

        try:
            # Try to get the volume from the pulse server.
            # use pipefail so an exception is thrown if pactl does not exist
            active_sink = False
            volume = 100
            for line in subprocess.check_output(
                "pactl list sinks".split(),
                env={"PULSE_SERVER": "127.0.0.1"},
                universal_newlines=True,
            ).splitlines():
                if active_sink and "Volume:" in line:
                    volume = re.search(r"(\d+)%", line).groups()[0]
                    break
                if "State: RUNNING" in line:
                    active_sink = True
            self.volume = int(volume) / 100
        except (FileNotFoundError, subprocess.CalledProcessError):
            with self.mopidy_command(important=True):
                # pulse is not installed or there is no server running.
                # get volume from mopidy
                self.volume = self.player.mixer.get_volume() / 100

    def start(self) -> None:
        """Starts the loop of the player."""
        self._loop()

    def progress(self) -> float:
        """Returns how far into the current song the playback is, in percent."""
        # the state is either pause or stop
        current_position = 0
        duration = 1
        with self.mopidy_command() as allowed:
            if allowed:
                current_position = self.player.playback.get_time_position()
                current_track = self.player.playback.get_current_track()
                if current_track is None:
                    return 0
                duration = current_track.length
        return 100 * current_position / duration

    def paused(self) -> bool:
        """Returns whether playback is currently paused."""
        # the state is either pause or stop
        paused = False
        with self.mopidy_command() as allowed:
            if allowed:
                paused = self.player.playback.get_state() != "playing"
        return paused

    @background_thread
    def _loop(self) -> None:
        """The main loop of the player.
        Takes a song from the queue and plays it until it is finished."""
        while True:

            catch_up = None
            if models.CurrentSong.objects.exists():
                # recover interrupted song from database
                current_song = models.CurrentSong.objects.get()

                # continue with the current song (approximately) where we last left
                song_provider = SongProvider.create(
                    self.musiq, external_url=current_song.external_url
                )
                duration = int(song_provider.get_metadata()["duration"])
                catch_up = round(
                    (timezone.now() - current_song.created).total_seconds() * 1000
                )
                if catch_up > duration * 1000:
                    catch_up = -1
            else:
                self.queue_semaphore.acquire()
                if not self.running:
                    break

                # select the next song depending on settings
                song: Optional[models.QueuedSong]
                if self.musiq.base.settings.voting_system:
                    with transaction.atomic():
                        song = self.queue.all().order_by("-votes", "index")[0]
                        song_id = song.id
                        self.queue.remove(song.id)
                elif self.shuffle:
                    index = random.randint(0, models.QueuedSong.objects.count() - 1)
                    song_id = models.QueuedSong.objects.all()[index].id
                    song = self.queue.remove(song_id)
                else:
                    # move the first song in the queue into the current song
                    song_id, song = self.queue.dequeue()

                if song is None:
                    # either the semaphore didn't match up with the actual count
                    # of songs in the queue or a race condition occured
                    logging.warning("dequeued on empty list")
                    continue

                current_song = models.CurrentSong.objects.create(
                    queue_key=song_id,
                    manually_requested=song.manually_requested,
                    votes=song.votes,
                    internal_url=song.internal_url,
                    external_url=song.external_url,
                    artist=song.artist,
                    title=song.title,
                    duration=song.duration,
                )

                self._handle_autoplay()

                try:
                    archived_song = models.ArchivedSong.objects.get(
                        url=current_song.external_url
                    )
                    votes: Optional[int]
                    if self.musiq.base.settings.voting_system:
                        votes = current_song.votes
                    else:
                        votes = None
                    if self.musiq.base.settings.logging_enabled:
                        models.PlayLog.objects.create(
                            song=archived_song,
                            manually_requested=current_song.manually_requested,
                            votes=votes,
                        )
                except (
                    models.ArchivedSong.DoesNotExist,
                    models.ArchivedSong.MultipleObjectsReturned,
                ):
                    pass

            self.musiq.update_state()

            playing = Event()

            @self.player.on_event("playback_state_changed")
            def _on_playback_state_changed(_event):
                playing.set()

            with self.mopidy_command(important=True):
                # after a restart consume may be set to False again, so make sure it is on
                self.player.tracklist.clear()
                self.player.tracklist.set_consume(True)
                self.player.tracklist.add(uris=[current_song.internal_url])
                self.player.playback.play()
                # mopidy can only seek when the song is playing
                playing.wait(timeout=1)
                if catch_up is not None and catch_up >= 0:
                    self.player.playback.seek(catch_up)

            self.musiq.update_state()

            if catch_up is None or catch_up >= 0:
                if not self._wait_until_song_end():
                    # there was a ConnectionError during waiting for the song to end
                    # we do not delete the current song but recover its state by restarting the loop
                    continue

            current_song.delete()

            if self.repeat:
                song_provider = SongProvider.create(
                    self.musiq, external_url=current_song.external_url
                )
                self.queue.enqueue(song_provider.get_metadata(), False)
                self.queue_semaphore.release()

            self.musiq.update_state()

            if (
                self.musiq.base.user_manager.partymode_enabled()
                and random.random() < self.musiq.base.settings.alarm_probability
            ):
                self.alarm_playing.set()
                self.musiq.base.lights.alarm_started()

                self.musiq.update_state()

                with self.mopidy_command(important=True):
                    self.player.tracklist.add(
                        uris=[
                            "file://"
                            + os.path.join(settings.BASE_DIR, "config/sounds/alarm.m4a")
                        ]
                    )
                    self.player.playback.play()
                playing.clear()
                playing.wait(timeout=1)
                self._wait_until_song_end()

                self.musiq.base.lights.alarm_stopped()
                self.musiq.update_state()
                self.alarm_playing.clear()

    def _wait_until_song_end(self) -> bool:
        """Wait until the song is over.
        Returns True when finished without errors, False otherwise."""
        # This is the event based approach. Unfortunately to error-prone.
        # playback_ended = Event()
        # @self.player.on_event('tracklist_changed')
        # def on_tracklist_change(event):
        #     playback_ended.set()
        # playback_ended.wait()
        error = False
        while True:
            with self.mopidy_command() as allowed:
                if allowed:
                    try:
                        if self.player.playback.get_state() == "stopped":
                            break
                    except (requests.exceptions.ConnectionError, MopidyError):
                        # error during state get, skip until reconnected
                        error = True
            time.sleep(0.1)
        return not error

    def _handle_autoplay(self, url: Optional[str] = None) -> None:
        if self.autoplay and models.QueuedSong.objects.count() == 0:
            if url is None:
                # if no url was specified, use the one of the current song
                try:
                    current_song = models.CurrentSong.objects.get()
                    url = current_song.external_url
                except (
                    models.CurrentSong.DoesNotExist,
                    models.CurrentSong.MultipleObjectsReturned,
                ):
                    return

            provider = SongProvider.create(self.musiq, external_url=url)
            try:
                suggestion = provider.get_suggestion()
                # The player loop is not restarted after error automatically.
                # As this function can raise several exceptions (it might do networking)
                # we catch every exception to make sure the loop keeps running
            except Exception as e:  # pylint: disable=broad-except
                logging.exception("error during suggestions for " + url)
            else:
                self.musiq.do_request_music(
                    "",
                    suggestion,
                    None,
                    False,
                    provider.type,
                    archive=False,
                    manually_requested=False,
                )

    @contextmanager
    def mopidy_command(self, important: bool = False) -> Iterator[bool]:
        """A context that should be used around every mopidy command used.
        Makes sure that commands occur sequentially, as mopidy can not handle parallel inputs.
        Use it like this:
        with self.mopidy_command() as allowed:
            if allowed:
                # mopidy command
        :param important: If True, wait until the lock is released.
        If not, return 'False' after a timeout."""
        timeout = 3
        if important:
            timeout = -1
        if self.player_lock.acquire(timeout=timeout):
            yield True
            self.player_lock.release()
        else:
            logging.warning("mopidy command could not be executed")
            yield False

    @disabled_when_voting
    @control
    def restart(self, _request: WSGIRequest) -> None:
        """Restarts the current song from the beginning."""
        with self.mopidy_command() as allowed:
            if allowed:
                self.player.playback.seek(0)

    @disabled_when_voting
    @control
    def seek_backward(self, _request: WSGIRequest) -> None:
        """Jumps back in the current song."""
        with self.mopidy_command() as allowed:
            if allowed:
                current_position = self.player.playback.get_time_position()
                self.player.playback.seek(current_position - self.SEEK_DISTANCE)

    @disabled_when_voting
    @control
    def play(self, _request: WSGIRequest) -> None:
        """Resumes the current song if it is paused.
        No-op if already playing."""
        with self.mopidy_command() as allowed:
            if allowed:
                self.player.playback.play()

    @disabled_when_voting
    @control
    def pause(self, _request: WSGIRequest) -> None:
        """Pauses the current song if it is playing.
        No-op if already paused."""
        with self.mopidy_command() as allowed:
            if allowed:
                self.player.playback.pause()

    @disabled_when_voting
    @control
    def seek_forward(self, _request: WSGIRequest) -> None:
        """Jumps forward in the current song."""
        with self.mopidy_command() as allowed:
            if allowed:
                current_position = self.player.playback.get_time_position()
                self.player.playback.seek(current_position + self.SEEK_DISTANCE)

    @disabled_when_voting
    @control
    def skip(self, _request: WSGIRequest) -> None:
        """Skips the current song and continues with the next one."""
        with self.mopidy_command() as allowed:
            if allowed:
                self.player.playback.next()

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
        self._handle_autoplay()

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
            with self.mopidy_command() as allowed:
                if allowed:
                    self.player.mixer.set_volume(round(self.volume * 100))

    @disabled_when_voting
    @control
    def remove_all(self, request: WSGIRequest) -> HttpResponse:
        """Empties the queue. Only admin is permitted to do this."""
        if not self.musiq.base.user_manager.is_admin(request.user):
            return HttpResponseForbidden()
        with self.mopidy_command() as allowed:
            if allowed:
                with transaction.atomic():
                    count = self.queue.count()
                    self.queue.all().delete()
                for _ in range(count):
                    self.queue_semaphore.acquire(blocking=False)
        return HttpResponse()

    @disabled_when_voting
    @control
    def prioritize(self, request: WSGIRequest) -> HttpResponse:
        """Prioritizes song by making it the first one in the queue."""
        key = request.POST.get("key")
        if key is None:
            return HttpResponseBadRequest()
        ikey = int(key)
        self.queue.prioritize(ikey)
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
            removed = self.queue.remove(ikey)
            self.queue_semaphore.acquire(blocking=False)
            # if we removed a song and it was added by autoplay,
            # we want it to be the new basis for autoplay
            if not removed.manually_requested:
                self._handle_autoplay(removed.external_url)
            else:
                self._handle_autoplay()
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
            self.queue.reorder(iprev_key, icur_key, inext_key)
        except ValueError:
            return HttpResponseBadRequest("request on old state")
        return HttpResponse()

    @control
    def vote_up(self, request: WSGIRequest) -> HttpResponse:
        """Increases the vote-count of the given song by one."""
        key = request.POST.get("key")
        if key is None:
            return HttpResponseBadRequest()
        ikey = int(key)

        models.CurrentSong.objects.filter(queue_key=ikey).update(votes=F("votes") + 1)
        self.queue.vote_up(ikey)
        return HttpResponse()

    @control
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
                and current_song.votes <= -self.musiq.base.settings.downvotes_to_kick
            ):
                with self.mopidy_command() as allowed:
                    if allowed:
                        self.player.playback.next()
        except models.CurrentSong.DoesNotExist:
            pass

        removed = self.queue.vote_down(
            ikey, -self.musiq.base.settings.downvotes_to_kick
        )
        # if we removed a song by voting, and it was added by autoplay,
        # we want it to be the new basis for autoplay
        if removed is not None:
            self.queue_semaphore.acquire(blocking=False)
            if not removed.manually_requested:
                self._handle_autoplay(removed.external_url)
            else:
                self._handle_autoplay()
        return HttpResponse()

    def start_loop(self) -> None:
        """Starts the playback main loop, only used for tests."""
        if self.running:
            return
        self.running = True
        self.start()

    def stop_loop(self) -> None:
        """Stops the playback main loop, only used for tests."""
        if not self.running:
            return
        self.running = False
        self.queue_semaphore.release()
