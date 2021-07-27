"""This module handles playback of music."""

from __future__ import annotations

import datetime
import logging
import os
import random
import time
from contextlib import contextmanager
from threading import Event
from typing import Iterator, Optional

import requests

from core.celery import app
from django.conf import settings as conf
from django.db import transaction, connection
from django.utils import timezone
from mopidyapi.client import MopidyAPI
from mopidyapi.exceptions import MopidyError

from core import redis
import core.models as models
from core import user_manager
from core.lights import controller as lights_controller
from core.musiq import musiq, controller
from core.settings import storage, settings

queue_changed = redis.Event("queue_changed")
buzzer_stopped = redis.Event("buzzer_stopped")

queue = models.QueuedSong.objects

# this lock is released when restarting mopidy (which happens in another Thread)
player_lock = redis.lock("player_lock", thread_local=False)


def start() -> None:
    """Initializes this module by starting the playback and buzzer loop."""
    _handle_buzzer.delay()
    _loop.delay()


def set_playback_error(error: bool) -> None:
    """Sets the playback error. Updates musiq state when the state changes."""
    if redis.get("playback_error"):
        if not error:
            redis.set("playback_error", False)
            musiq.update_state()
            settings.update_state()
    else:
        if error:
            redis.set("playback_error", True)
            musiq.update_state()
            settings.update_state()


class Playback:
    """Class containing all playback related methods."""

    def __init__(self):
        # the celery worker needs its own player instance.
        # if we use a module-wide instance, methods can be used,
        # but events do not register correctly (probably due to thread boundary)
        if conf.TESTING:
            # to reduce the amount of created mopidy connections,
            # use the controller's instance during testing
            # this works because everything is run in a single process
            self.player = controller.player
        else:
            self.player: MopidyAPI = MopidyAPI(host=conf.MOPIDY_HOST)
        self.playback_started = Event()
        redis.set("playing", False)

        queue.delete_placeholders()

        with mopidy_command(important=True):
            self.player.playback.stop()
            self.player.tracklist.clear()
            # make songs disappear from tracklist after being played
            self.player.tracklist.set_consume(True)

        @self.player.on_event("track_playback_started")
        def _on_playback_started(_event) -> None:
            self.playback_started.set()

    def play_alarm(self, interrupt=False) -> None:
        """Play the alarm sound. If specified, interrupts the currently playing song."""
        redis.set("alarm_playing", True)
        lights_controller.alarm_started()
        self.playback_started.clear()

        with mopidy_command(important=True):
            # interrupt the current song if its playing
            if interrupt:
                self.player.tracklist.clear()
            self.player.tracklist.add(
                uris=[
                    "file://" + os.path.join(conf.BASE_DIR, "config/sounds/alarm.m4a")
                ]
            )
            self.player.playback.play()
        self.playback_started.wait(timeout=1)

        musiq.update_state()
        self.wait_until_song_end()

        lights_controller.alarm_stopped()
        redis.set("alarm_playing", False)

        if not interrupt:
            # if no song immediately continues playing, a manual state update is needed
            musiq.update_state()

    def wait_until_song_end(self) -> bool:
        """Wait until the song is over.
        Returns True when finished without errors, False otherwise."""
        # This is the event based approach. Unfortunately too error-prone.
        # If mopidy crashes/restarts for example, no track_playback_ended event is sent
        # playback_ended.wait()
        error = False
        while True:
            with mopidy_command() as allowed:
                if allowed:
                    try:
                        if self.player.playback.get_state() == "stopped":
                            break
                    except (requests.exceptions.ConnectionError, MopidyError):
                        # error during state get, skip until reconnected
                        error = True
            time.sleep(0.1)
            if redis.get("stop_playback_loop"):
                # in order to stop the playback thread, return False, making the main loop restart.
                # it will check this variable again and terminate itself.
                return False
            if redis.get("alarm_requested"):
                redis.set("alarm_requested", False)
                self.play_alarm(interrupt=True)
                # the current song was interrupted and needs to be resumed at the correct position
                # returning False will notify the main loop about this interruption,
                # making it restart the song correctly
                current_song = models.CurrentSong.objects.get()
                # we don't want the song to skip over the time when the alarm was playing
                # thus, we offset the creation date of the current song by the length of the alarm
                # Warning: if this duration does not fit the duration of the actual alarm,
                # Raveberry's internal state gets desynced and weird errors happen
                current_song.created += datetime.timedelta(
                    seconds=musiq.get_alarm_metadata()["duration"]
                )
                current_song.save()

                return False
        return not error

    def loop(self) -> None:
        """The main loop of the player.
        Takes a song from the queue and plays it until it is finished."""
        while True:

            if redis.get("stop_playback_loop"):
                break

            catch_up = None
            self.playback_started.clear()

            if models.CurrentSong.objects.exists():
                # recover interrupted song from database
                current_song = models.CurrentSong.objects.get()

                # continue with the current song (approximately) where we last left
                if storage.get("paused"):
                    catch_up = round(
                        (
                            current_song.last_paused - current_song.created
                        ).total_seconds()
                        * 1000
                    )
                else:
                    catch_up = round(
                        (timezone.now() - current_song.created).total_seconds() * 1000
                    )
                if catch_up > current_song.duration * 1000:
                    catch_up = -1
            else:
                if queue.count() == 0:
                    queue_changed.wait()
                    queue_changed.clear()

                    # restart the loop to check again whether songs are available
                    # in case of a false wakeup this causes as to wait again
                    continue

                # select the next song depending on settings
                song: Optional[models.QueuedSong]
                if storage.get("voting_enabled"):
                    with transaction.atomic():
                        song = queue.confirmed().order_by("-votes", "index")[0]
                        song_id = song.id
                        queue.remove(song.id)
                elif storage.get("shuffle"):
                    confirmed = queue.confirmed()
                    index = random.randint(0, confirmed.count() - 1)
                    song_id = confirmed[index].id
                    song = queue.remove(song_id)
                else:
                    # move the first song in the queue into the current song
                    song_id, song = queue.dequeue()

                if song is None:
                    # either the semaphore didn't match up with the actual count
                    # of songs in the queue or a race condition occured
                    logging.warning("dequeued on empty list")
                    continue

                if song.internal_url == "alarm":
                    self.play_alarm()
                    continue

                # stop backup stream.
                # when the dequeued song starts playing, the backup stream playback is stopped
                redis.set("backup_playing", False)

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

                handle_autoplay()

                try:
                    archived_song = models.ArchivedSong.objects.get(
                        url=current_song.external_url
                    )
                    votes: Optional[int]
                    if storage.get("voting_enabled"):
                        votes = current_song.votes
                    else:
                        votes = None
                    if storage.get("logging_enabled"):
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

            with mopidy_command(important=True):
                # after a restart consume may be set to False again, so make sure it is on
                self.player.tracklist.clear()
                self.player.tracklist.set_consume(True)
                self.player.tracklist.add(uris=[current_song.internal_url])
                # temporarily mute mopidy in case we need to seek but mopidy does not react directly
                # this allows us to seek first and then unmute, preventing audible skips
                volume = self.player.mixer.get_volume()
                if catch_up is not None and catch_up >= 0:
                    self.player.mixer.set_volume(0)
                # mopidy can only seek when the song is playing
                # also we do not continue without the playing state properly set.
                # otherwise waiting might exit before the song started
                self.player.playback.play()
                if not self.playback_started.wait(timeout=1):
                    # mopidy did not acknowledge that it started the song
                    # to make sure it is not in an error state,
                    # restart the loop and retry to start the song
                    # also prevents "queue-eating" bug,
                    # where mopidy in a failed state would refuse to play any song,
                    # but raveberry keeps on sending songs from the queue
                    logging.warning("playback_started event did not trigger")
                    set_playback_error(True)
                    self.player.mixer.set_volume(volume)
                    continue
                set_playback_error(False)
                if catch_up is not None and catch_up >= 0:
                    self.player.playback.seek(catch_up)
                    if storage.get("paused"):
                        self.player.playback.pause()
                    self.player.mixer.set_volume(volume)
            redis.set("playing", True)

            # needs some more testing but could prevent "eating the queue" bug
            # if not started_playing and not settings.DOCKER:
            #    logging.error(
            #        "Mopidy did not start playing the song in the timeout. Error assumed.\n"
            #        "Usually faulty outputs are the reason, config is reset to local output.\n"
            #        "Consult mopidy's log for more information.\n"
            #    )
            #    # reset to pulse device 0
            #    core.settings.sound._set_output("0")
            #    # recover the current song by restarting the loop
            #    continue

            musiq.update_state()

            # don't wait for the song to end if catch_up is negative (=the song should be skipped)
            if catch_up is None or catch_up >= 0:
                if not self.wait_until_song_end():
                    # there was an error while waiting for the song to end
                    # This happens when we could not connect to mopidy (ConnectionError)
                    # or when an interrupting alarm was initiated.
                    # we do not delete the current song but recover its state by restarting the loop
                    storage.set("paused", False)
                    redis.set("playing", False)
                    continue
            # Allowing new songs to start playing while paused introduces many edge cases
            # Instead of dealing with them, always start playback when skipping a paused song
            storage.set("paused", False)
            redis.set("playing", False)

            current_song.delete()

            if storage.get("repeat"):
                queue.enqueue(
                    {
                        "artist": current_song.artist,
                        "title": current_song.title,
                        "duration": current_song.duration,
                        "internal_url": current_song.internal_url,
                        "external_url": current_song.external_url,
                        "stream_url": current_song.stream_url,
                    },
                    False,
                )
                queue_changed.set()

            if user_manager.partymode_enabled() and random.random() < storage.get(
                "alarm_probability"
            ):
                self.play_alarm()

            if not queue.exists() and storage.get("backup_stream"):
                redis.set("backup_playing", True)
                # play backup stream
                self.player.tracklist.add(uris=[storage.get("backup_stream")])
                self.player.playback.play()

            musiq.update_state()


@app.task
def _loop() -> None:
    playback = Playback()
    playback.loop()
    connection.close()


@app.task
def _handle_buzzer() -> None:
    try:
        import gpiozero
    except ModuleNotFoundError:
        return
    buzzer = gpiozero.Button(16)
    last_press = timezone.now() - datetime.timedelta(
        seconds=storage.get("buzzer_cooldown")
    )

    def on_press():
        nonlocal last_press

        # do not allow the buzzer to be pressed too frequently
        if (timezone.now() - last_press).total_seconds() < storage.get(
            "buzzer_cooldown"
        ):
            logging.warning("buzzer pressed too quickly")
            return
        # do not allow an alarm to be triggered while one is already playing
        # or when an alarm is currently in the process of being played
        if redis.get("alarm_playing") or redis.get("alarm_requested"):
            logging.warning("last buzzer alarm not yet finished")
            return
        last_press = timezone.now()

        trigger_alarm()

    buzzer.when_pressed = on_press

    # wait until this task is told to exit
    buzzer_stopped.wait()


def trigger_alarm() -> None:
    """Initiate an alarm."""
    if redis.get("playing"):
        # if a song is currently playing, inform the loop waiting for the song to end
        # about this alarm. It will interrupt the current song and play the alarm
        redis.set("alarm_requested", True)
    else:
        # insert a special queue song to wake up the main loop and make it play the alarm
        queue.enqueue(musiq.get_alarm_metadata(), True)
        queue_changed.set()


def handle_autoplay(url: Optional[str] = None) -> None:
    """Checks whether to add a song by autoplay and does so if necessary.
    :param url: if given, this url is used to find the next autoplayed song.
    Otherwise, the current song is used."""
    if storage.get("autoplay") and models.QueuedSong.objects.count() == 0:
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

        from core.musiq.song_provider import SongProvider

        provider = SongProvider.create(external_url=url)
        try:
            suggestion = provider.get_suggestion()
            # The player loop is not restarted after error automatically.
            # As this function can raise several exceptions (it might do networking)
            # we catch every exception to make sure the loop keeps running
        except Exception as e:  # pylint: disable=broad-except
            logging.exception("error during suggestions for %s: %s", url, e)
        else:
            musiq.do_request_music(
                "",
                suggestion,
                None,
                False,
                provider.type,
                archive=False,
                manually_requested=False,
            )


@contextmanager
def mopidy_command(important: bool = False) -> Iterator[bool]:
    """A context that should be used around every mopidy command used.
    Makes sure that commands occur sequentially, as mopidy can not handle parallel inputs.
    Use it like this:
    with mopidy_command() as allowed:
        if allowed:
            # mopidy command
    :param important: If True, wait until the lock is released.
    If not, return 'False' after a timeout."""
    timeout = 3
    if important:
        timeout = None
    if player_lock.acquire(blocking_timeout=timeout):
        yield True
        player_lock.release()
    else:
        logging.warning("mopidy command could not be executed")
        set_playback_error(True)
        yield False


def stop() -> None:
    """Stops the playback main loop, only used for tests."""
    redis.set("stop_playback_loop", True)
    queue_changed.set()
