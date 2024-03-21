"""This module defines the abstract interface to interface with playback software."""

from django.conf import settings as conf
from mopidyapi.client import MopidyAPI

from core import redis
from core.musiq import musiq
from core.settings import settings


def set_playback_error(error: bool) -> None:
    """Sets the playback error. Updates musiq state when the state changes."""
    if redis.get("playback_error"):
        if not error:
            redis.put("playback_error", False)
            musiq.update_state()
            settings.update_state()
    else:
        if error:
            redis.put("playback_error", True)
            musiq.update_state()
            settings.update_state()


class Player:
    """Class containing methods to interface with playback software."""

    def start_song(self, song, catch_up: float):
        """Start's the specified song.
        Raises a PlaybackError on error."""
        raise NotImplementedError

    def should_stop_waiting(self, previous_error: bool) -> bool:
        """check whether the main loop should stop waiting for the song to end.
        Returns True if it should stop waiting, False otherwise.
        Raises PlaybackError on error."""
        return False

    def play_alarm(self, interrupt: bool, alarm_path: str) -> None:
        raise NotImplementedError

    def play_backup_stream(self):
        raise NotImplementedError


def _active_player():
    """Looks up the currently active player and returns the respective class.
    This is necessary since the requests have no reference to a player object,
    so all methods need to be static.
    Thus no inheritance is possible, and needs to be faked here."""

    active_player = redis.get("active_player")
    if active_player == "mopidy":
        from core.musiq import mopidy_player

        return mopidy_player
    elif active_player == "spotify":
        from core.musiq import spotify_player

        return spotify_player
    elif active_player == "fake":
        from core.musiq import fake_player

        return fake_player


def restart() -> None:
    """Restarts the current song from the beginning."""
    _active_player().restart()


def seek_backward(seek_distance: float) -> None:
    """Jumps back in the current song."""
    _active_player().seek_backward(seek_distance)


def play() -> None:
    """Resumes the current song if it is paused.
    No-op if already playing."""
    _active_player().play()


def pause() -> None:
    """Pauses the current song if it is playing.
    No-op if already paused."""
    _active_player().pause()


def seek_forward(seek_distance: float) -> None:
    """Jumps forward in the current song."""
    _active_player().seek_forward(seek_distance)


def skip() -> None:
    """Skips the current song and continues with the next one."""
    _active_player().skip()


def set_volume(volume) -> None:
    """Sets the playback volume.
    value has to be a float between 0 and 1."""
    _active_player().set_volume(volume)
