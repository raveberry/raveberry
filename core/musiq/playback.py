"""This module handles playback of music."""

from __future__ import annotations

import datetime
import logging
import os
import random
import time
from contextlib import contextmanager
from threading import Event
from threading import Lock
from threading import Semaphore
from typing import Iterator, Optional, TYPE_CHECKING

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from mopidyapi.client import MopidyAPI
from mopidyapi.exceptions import MopidyError

import core.models as models
from core.musiq.song_provider import SongProvider
from core.util import background_thread

if TYPE_CHECKING:
    from core.musiq.musiq import Musiq


class Playback:
    """This class handles music playback."""

    # this has to be a class variable
    # so the manager of the queue can access it without a player object
    # a semaphore that indicates whether any _completed_ songs are available in the queue
    # placeholders do not count towards the internal counter
    queue_semaphore: Semaphore = None  # type: ignore

    def __init__(self, musiq: "Musiq") -> None:
        self.musiq = musiq

        self.queue = models.QueuedSong.objects
        self.alarm_playing: Event = Event()
        self.alarm_requested: Event = Event()
        self.backup_playing: Event = Event()
        self.running = True

        self.player: MopidyAPI = MopidyAPI(host=settings.MOPIDY_HOST)
        self.player_lock = Lock()

        self.playing = Event()

        @self.player.on_event("playback_state_changed")
        def _on_playback_state_changed(event):
            if event.new_state == "playing":
                self.playing.set()

    def start(self) -> None:
        self.queue.delete_placeholders()
        Playback.queue_semaphore = Semaphore(self.queue.count())

        with self.mopidy_command(important=True):
            self.player.playback.stop()
            self.player.tracklist.clear()
            # make songs disappear from tracklist after being played
            self.player.tracklist.set_consume(True)
        self.handle_buzzer()
        self._loop()

    def progress(self, important=False) -> float:
        """Returns how far into the current song the playback is, in percent."""
        # the state is either pause or stop
        current_position = 0
        duration = 1
        with self.mopidy_command(important=important) as allowed:
            if allowed:
                current_position = self.player.playback.get_time_position()
                current_track = self.player.playback.get_current_track()
                if current_track is None or self.backup_playing.is_set():
                    return 0
                try:
                    duration = current_track.length
                except AttributeError:
                    # the backup stream does not have a length attribute
                    duration = 60 * 60 * 24
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
            self.playing.clear()

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
                if self.musiq.base.settings.basic.voting_system:
                    with transaction.atomic():
                        song = self.queue.confirmed().order_by("-votes", "index")[0]
                        song_id = song.id
                        self.queue.remove(song.id)
                elif self.musiq.controller.shuffle:
                    confirmed = self.queue.confirmed()
                    index = random.randint(0, confirmed.count() - 1)
                    song_id = confirmed[index].id
                    song = self.queue.remove(song_id)
                else:
                    # move the first song in the queue into the current song
                    song_id, song = self.queue.dequeue()

                if song.internal_url == "alarm":
                    self.play_alarm()
                    continue

                if song is None:
                    # either the semaphore didn't match up with the actual count
                    # of songs in the queue or a race condition occured
                    logging.warning("dequeued on empty list")
                    continue

                if self.backup_playing.is_set():
                    # stop backup stream.
                    # when the dequeued song starts playing, the backup stream playback is stopped
                    self.backup_playing.clear()

                current_song = models.CurrentSong.objects.create(
                    queue_key=song_id,
                    manually_requested=song.manually_requested,
                    votes=song.votes,
                    internal_url=song.internal_url,
                    external_url=song.external_url,
                    stream_url=song.stream_url,
                    artist=song.artist,
                    title=song.title,
                    duration=song.duration,
                )

                self.handle_autoplay()

                try:
                    archived_song = models.ArchivedSong.objects.get(
                        url=current_song.external_url
                    )
                    votes: Optional[int]
                    if self.musiq.base.settings.basic.voting_system:
                        votes = current_song.votes
                    else:
                        votes = None
                    if self.musiq.base.settings.basic.logging_enabled:
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

            with self.mopidy_command(important=True):
                # after a restart consume may be set to False again, so make sure it is on
                self.player.tracklist.clear()
                self.player.tracklist.set_consume(True)
                self.player.tracklist.add(uris=[current_song.internal_url])
                # temporarily mute mopidy in case we need to seek but mopidy does not react directly
                # this allows us to seek first and then unmute, preventing audible skips
                volume = self.player.mixer.get_volume()
                self.player.mixer.set_volume(0)
                self.player.playback.play()
                # mopidy can only seek when the song is playing
                started_playing = self.playing.wait(timeout=1)
                if not started_playing:
                    # after mopidy restarts, the song is playing but the event is not fired
                    # thus, playing is not set by the callback. We set it explicitly in this case
                    self.playing.set()
                self.player.mixer.set_volume(volume)
                if catch_up is not None and catch_up >= 0:
                    self.player.playback.seek(catch_up)

                # needs some more testing but could prevent "eating the queue" bug
                # if not started_playing and not settings.DOCKER:
                #    logging.error(
                #        "Mopidy did not start playing the song in the timeout. Error assumed.\n"
                #        "Usually faulty outputs are the reason, config is reset to local output.\n"
                #        "Consult mopidy's log for more information.\n"
                #    )
                #    # reset to pulse device 0
                #    self.musiq.base.settings.sound._set_output("0")
                #    # recover the current song by restarting the loop
                #    continue

            self.musiq.update_state()

            if catch_up is None or catch_up >= 0:
                if not self._wait_until_song_end():
                    # there was an error while waiting for the song to end
                    # This happens when we could not connect to mopidy (ConnectionError)
                    # or when an interrupting alarm was initiated.
                    # we do not delete the current song but recover its state by restarting the loop
                    continue

            current_song.delete()

            if self.musiq.controller.repeat:
                song_provider = SongProvider.create(
                    self.musiq, external_url=current_song.external_url
                )
                self.queue.enqueue(song_provider.get_metadata(), False)
                self.queue_semaphore.release()

            if (
                self.musiq.base.user_manager.partymode_enabled()
                and random.random() < self.musiq.base.settings.basic.alarm_probability
            ):
                self.play_alarm()

            if not self.queue.exists() and self.musiq.base.settings.sound.backup_stream:
                self.backup_playing.set()
                # play backup stream
                self.player.tracklist.add(
                    uris=[self.musiq.base.settings.sound.backup_stream]
                )
                self.player.playback.play()

            self.musiq.update_state()

    def play_alarm(self, interrupt=False) -> None:
        self.alarm_playing.set()
        self.musiq.base.lights.alarm_started()

        self.playing.clear()
        with self.mopidy_command(important=True):
            if interrupt:
                self.player.tracklist.clear()
            self.player.tracklist.add(
                uris=[
                    "file://"
                    + os.path.join(settings.BASE_DIR, "config/sounds/alarm.m4a")
                ]
            )
            self.player.playback.play()
        self.playing.wait(timeout=1)
        started_playing = self.playing.wait(timeout=1)
        if not started_playing:
            self.playing.set()

        self.musiq.update_state()

        self._wait_until_song_end()

        self.musiq.base.lights.alarm_stopped()
        self.alarm_playing.clear()

    def _wait_until_song_end(self) -> bool:
        """Wait until the song is over.
        Returns True when finished without errors, False otherwise."""
        # This is the event based approach. Unfortunately too error-prone.
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
            if self.alarm_requested.is_set():
                self.alarm_requested.clear()
                self.play_alarm(interrupt=True)
                # the current song was interrupted and needs to be resumed at the correct position
                # returning False will notify the main loop about this interruption,
                # making it restart the song correctly
                current_song = models.CurrentSong.objects.get()
                # we don't want the song to skip over the time when the alarm was playing
                # thus, we offset the creation date of the current song by the length of the alarm
                # Warning: if this duration does not fit the duration of the actual alarm,
                # Raveberry's internal state get's desynced and weird errors happen
                current_song.created += datetime.timedelta(seconds=10)
                current_song.save()

                return False
        return not error

    @background_thread
    def handle_buzzer(self) -> None:
        try:
            import gpiozero
        except ModuleNotFoundError:
            return
        buzzer = gpiozero.Button(16)
        last_press = timezone.now() - datetime.timedelta(
            seconds=self.musiq.base.settings.basic.buzzer_cooldown
        )
        while True:
            buzzer.wait_for_release()
            buzzer.wait_for_press()
            # do not allow the buzzer to be pressed too frequently
            if (
                timezone.now() - last_press
            ).total_seconds() < self.musiq.base.settings.basic.buzzer_cooldown:
                logging.warning("buzzer pressed too quickly")
                continue
            # do not allow an alarm to be triggered while one is already playing
            # or when an alarm is currently in the process of being played
            if self.alarm_playing.is_set() or self.alarm_requested.is_set():
                logging.warning("last buzzer alarm not yet finished")
                continue

            last_press = timezone.now()
            if self.playing.is_set():
                # if a song is currently playing, inform the loop waiting for the song to end
                # about this alarm. It will interrupt the current song and play the alarm
                self.alarm_requested.set()
            else:
                # insert a special queue song to wake up the main loop and make it play the alarm
                self.queue.enqueue(
                    {
                        "artist": "Raveberry",
                        "title": "ALARM!",
                        "duration": 10,
                        "internal_url": "alarm",
                        "external_url": "alarm",
                    },
                    True,
                )
                self.queue_semaphore.release()

    def handle_autoplay(self, url: Optional[str] = None) -> None:
        """Checks whether to add a song by autoplay and does so if necessary.
        :param url: if given, this url is used to find the next autoplayed song.
        Otherwise, the current song is used."""
        if self.musiq.controller.autoplay and models.QueuedSong.objects.count() == 0:
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
                logging.exception("error during suggestions for %s: %s", url, e)
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

    def start_loop(self) -> None:
        """Starts the playback main loop, only used for tests."""
        if self.running:
            return
        self.running = True
        self._loop()

    def stop_loop(self) -> None:
        """Stops the playback main loop, only used for tests."""
        if not self.running:
            return
        self.running = False
        self.queue_semaphore.release()
