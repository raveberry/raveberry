"""This module interfaces with spotify."""

import logging
from contextlib import contextmanager
from typing import Iterator

import requests.exceptions
from spotipy import SpotifyException, SpotifyOauthError

from core.musiq.playback import PlaybackError
from core.musiq import player
from core.musiq.spotify import Spotify
from core.musiq import song_utils


@contextmanager
def spotify_api(reraise: bool = False) -> Iterator:
    """A context that should be used around every spotify api playback call.
    Catches common exceptions and deals with them."""
    try:
        yield
        # after a successful api call, there is no error with spotify
        player.set_playback_error(False)
    except (
        SpotifyException,
        SpotifyOauthError,
        requests.exceptions.ConnectionError,
    ) as e:
        logging.warning("Spotify API Error: %s", e)
        player.set_playback_error(True)
        if reraise:
            raise e


class SpotifyPlayer(player.Player):
    """Class containing methods to interface with Spotify."""

    def start_song(self, song, catch_up: float):
        if song_utils.determine_url_type(song.external_url) != "spotify":
            logging.warning("tried to play non-spotify song with spotify player")
            raise PlaybackError("Not a Spotify song")
        try:
            with spotify_api(reraise=True):
                # if catch_up is not None and catch_up >= 0:
                #    volume = Spotify.api.current_playback()["device"]["volume_percent"]
                #    Spotify.api.volume(0)
                Spotify.api.start_playback(uris=[song.internal_url])
                if catch_up is not None and catch_up >= 0:
                    Spotify.api.seek_track(catch_up)
                    # Spotify.api.volume(volume)
        except (
            SpotifyException,
            SpotifyOauthError,
            requests.exceptions.ConnectionError,
        ):
            raise PlaybackError("Spotify API error")

    def play_alarm(self, interrupt: bool, alarm_path: str) -> None:
        # since the sounds can not be played on Spotify, we only pause here to have
        # some time so they can be played some other way
        pause()

    def play_backup_stream(self):
        # Spotify can't play arbitrary internet streams
        pass


def restart() -> None:
    with spotify_api():
        Spotify.api.seek_track(0)


def seek_backward(seek_distance: float) -> None:
    with spotify_api():
        # TODO: Spotify often returns None in progress_ms. then we cannot seek
        current_position = Spotify.api.current_playback()["progress_ms"]
        if current_position:
            Spotify.api.seek_track(current_position - seek_distance * 1000)


def play() -> None:
    with spotify_api():
        Spotify.api.start_playback()


def pause() -> None:
    with spotify_api():
        Spotify.api.pause_playback()


def seek_forward(seek_distance: float) -> None:
    with spotify_api():
        current_position = Spotify.api.current_playback()["progress_ms"]
        if current_position:
            Spotify.api.seek_track(current_position + seek_distance * 1000)


def skip() -> None:
    with spotify_api():
        Spotify.api.next_track()


def set_volume(volume) -> None:
    with spotify_api():
        logging.error("trying to set volume")
        Spotify.api.volume(round(volume * 100))
        logging.error("finished to set volume")
