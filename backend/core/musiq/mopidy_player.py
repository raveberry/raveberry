"""This module interfaces with mopidy."""

import logging
import urllib.parse
from contextlib import contextmanager
from typing import Iterator, Optional
from threading import Event

import requests
from django.conf import settings as conf
from mopidyapi.client import MopidyAPI
from mopidyapi.exceptions import MopidyError


from core import redis
from core.musiq.playback import PlaybackError
from core.settings import storage
from core.musiq import player

# this lock is released when restarting mopidy (which happens in another Thread)
mopidy_lock = redis.connection.lock("mopidy_lock", thread_local=False)

# this creates two PLAYER objects, once in the playback worker
# and once in the request handler
# during testing, both are the same process and thus only one instance is created
PLAYER = MopidyAPI(host=conf.MOPIDY_HOST, port=conf.MOPIDY_PORT)


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
    timeout: Optional[int] = 3
    if important:
        timeout = None
    if mopidy_lock.acquire(blocking_timeout=timeout):
        yield True
        mopidy_lock.release()
    else:
        logging.warning("mopidy command could not be executed")
        player.set_playback_error(True)
        yield False


class MopidyPlayer(player.Player):
    """Class containing methods to interface with mopidy."""

    def __init__(self):
        self.playback_started = Event()

        with mopidy_command(important=True):
            PLAYER.playback.stop()
            PLAYER.tracklist.clear()
            # make songs disappear from tracklist after being played
            PLAYER.tracklist.set_consume(True)

        @PLAYER.on_event("track_playback_started")
        def _on_playback_started(_event) -> None:
            self.playback_started.set()

    def start_song(self, song, catch_up: float):
        with mopidy_command(important=True):
            # after a restart consume may be set to False again, so make sure it is on
            PLAYER.tracklist.clear()
            PLAYER.tracklist.set_consume(True)
            PLAYER.tracklist.add(uris=[song.internal_url])
            # temporarily mute mopidy in case we need to seek but mopidy does not react directly
            # this allows us to seek first and then unmute, preventing audible skips
            volume = PLAYER.mixer.get_volume()
            if catch_up is not None and catch_up >= 0:
                PLAYER.mixer.set_volume(0)
            # mopidy can only seek when the song is playing
            # also we do not continue without the playing state properly set.
            # otherwise waiting might exit before the song started
            PLAYER.playback.play()
            if not self.playback_started.wait(timeout=1):
                # mopidy did not acknowledge that it started the song
                # to make sure it is not in an error state,
                # restart the loop and retry to start the song
                # also prevents "queue-eating" bug,
                # where mopidy in a failed state would refuse to play any song,
                # but raveberry keeps on sending songs from the queue
                logging.warning("playback_started event did not trigger")
                player.set_playback_error(True)
                PLAYER.mixer.set_volume(volume)
                raise PlaybackError("playback_started event did not trigger")
            player.set_playback_error(False)
            if catch_up is not None and catch_up >= 0:
                # instead of seeking to the specified time
                # mopidy sometimes just starts the song from the beginning
                # checking the time position before and after seeking
                # prevents this from happening for some reason
                PLAYER.playback.get_time_position()
                PLAYER.playback.seek(catch_up)
                PLAYER.playback.get_time_position()
                if redis.get("paused"):
                    PLAYER.playback.pause()
                PLAYER.mixer.set_volume(volume)

    def should_stop_waiting(self, previous_error: bool) -> bool:
        error = False
        with mopidy_command() as allowed:
            if allowed:
                try:
                    # if there was an error previously, then a stopped state means
                    # that mopidy is back up. stop waiting and continue the main loop
                    if PLAYER.playback.get_state() == "stopped" and previous_error:
                        return True
                    # previously we also used this to check for the song end,
                    # but this is now done via the start point and duration of a song
                except (requests.exceptions.ConnectionError, MopidyError):
                    # error during state get, skip until reconnected
                    error = True
        if error:
            # raise outside of the with block to free resources
            raise PlaybackError
        return False

    def play_alarm(self, interrupt: bool, alarm_path: str) -> None:
        self.playback_started.clear()
        with mopidy_command(important=True):
            # interrupt the current song if its playing
            if interrupt:
                PLAYER.tracklist.clear()

            PLAYER.tracklist.add(uris=["file://" + urllib.parse.quote(alarm_path)])
            PLAYER.playback.play()
        self.playback_started.wait(timeout=1)

    def play_backup_stream(self):
        PLAYER.tracklist.add(uris=[storage.get("backup_stream")])
        PLAYER.playback.play()


def restart() -> None:
    with mopidy_command() as allowed:
        if allowed:
            PLAYER.playback.seek(0)


def seek_backward(seek_distance: float) -> None:
    with mopidy_command() as allowed:
        if allowed:
            current_position = PLAYER.playback.get_time_position()
            PLAYER.playback.seek(current_position - seek_distance * 1000)


def play() -> None:
    with mopidy_command() as allowed:
        if allowed:
            PLAYER.playback.play()


def pause() -> None:
    with mopidy_command() as allowed:
        if allowed:
            PLAYER.playback.pause()


def seek_forward(seek_distance: float) -> None:
    with mopidy_command() as allowed:
        if allowed:
            current_position = PLAYER.playback.get_time_position()
            PLAYER.playback.seek(current_position + seek_distance * 1000)


def skip() -> None:
    with mopidy_command() as allowed:
        if allowed:
            PLAYER.playback.next()


def set_volume(volume) -> None:
    # change mopidy's volume
    with mopidy_command() as allowed:
        if allowed:
            PLAYER.mixer.set_volume(round(volume * 100))
