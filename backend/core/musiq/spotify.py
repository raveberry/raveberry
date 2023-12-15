"""This module contains all Spotify related code."""

from __future__ import annotations

import json
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import spotipy
from django.http.response import HttpResponse
from spotipy import SpotifyOAuth, SpotifyStateError

from core.musiq import song_utils
from core.musiq.playlist_provider import PlaylistProvider
from core.musiq.song_provider import SongProvider
from core.musiq.spotify_web import OAuthClient
from core.settings import storage
from core import redis


class staticproperty(property):
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()


def _get_auth_response_storage(self, open_browser=False):
    response = storage.get("spotify_authorized_url")
    state, code = SpotifyOAuth.parse_auth_response_url(response)
    if self.state is not None and self.state != state:
        raise SpotifyStateError(self.state, state)
    return code


class DatabaseCacheHandler(spotipy.CacheHandler):
    """A cache handler for spotipy OAuth that stores the token info in the database."""

    def get_cached_token(self):
        token_info = storage.get("spotipy_token_info")
        if not token_info:
            return None
        return json.loads(token_info)

    def save_token_to_cache(self, token_info):
        storage.put("spotipy_token_info", json.dumps(token_info))


class Spotify:
    """This class contains code for both the song and playlist provider"""

    _device_api = None  # type: ignore[assignment]
    _mopidy_api = None  # type: ignore[assignment]

    @staticmethod
    def device_api():
        client_id = storage.get(key="spotify_device_client_id")
        client_secret = storage.get(key="spotify_device_client_secret")
        redirect_uri = storage.get(key="spotify_redirect_uri")
        scope = "user-read-playback-state user-modify-playback-state playlist-read-private playlist-read-collaborative user-library-read"

        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            cache_handler=DatabaseCacheHandler(),
        )
        auth_manager._get_auth_response_interactive = (
            _get_auth_response_storage.__get__(auth_manager)
        )

        return spotipy.Spotify(auth_manager=auth_manager)

    @staticmethod
    def mopidy_api():
        client_id = storage.get(key="spotify_mopidy_client_id")
        client_secret = storage.get(key="spotify_mopidy_client_secret")
        return OAuthClient(
            base_url="https://api.spotify.com/v1",
            refresh_url="https://auth.mopidy.com/spotify/token",
            client_id=client_id,
            client_secret=client_secret,
        )

    @staticmethod
    def create_device_api():
        Spotify._device_api = Spotify.device_api()

    @staticmethod
    def create_mopidy_api():
        Spotify._mopidy_api = Spotify.mopidy_api()

    @staticproperty
    def api(cls):
        """Returns the spotify client if it was already created.
        If not, it is created using the spotify credentials from the database."""
        if redis.get("active_player") == "spotify":
            if cls._device_api is None:
                cls.create_device_api()
            return cls._device_api
        elif redis.get("active_player") == "mopidy":
            if cls._mopidy_api is None:
                cls.create_mopidy_api()
            return cls._mopidy_api

    def get_search_suggestions(
        self, query: str, playlist: bool
    ) -> List[Tuple[str, str]]:
        """Returns a list of suggested items for the given query.
        Returns playlists if :param playlist: is True, songs otherwise."""
        result = self.api.search(
            query, limit=20, type="playlist" if playlist else "track"
        )

        if playlist:
            items = result["playlists"]["items"]
        else:
            items = result["tracks"]["items"]

        suggestions = []
        for item in items:
            external_url = item["external_urls"]["spotify"]
            title = item["name"]
            if playlist:
                displayname = title
            else:
                artist = item["artists"][0]["name"]
                # apply filter from the settings
                if song_utils.is_forbidden(artist) or song_utils.is_forbidden(title):
                    continue
                displayname = song_utils.displayname(artist, title)
            suggestions.append((displayname, external_url))

        # remove duplicates and filter by keywords
        chosen_displaynames = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion[0] in chosen_displaynames:
                continue
            unique_suggestions.append(suggestion)
            chosen_displaynames.add(suggestion[0])
        return unique_suggestions


class SpotifySongProvider(SongProvider, Spotify):
    """This class handles songs from Spotify."""

    @staticmethod
    def get_id_from_external_url(url: str) -> str:
        return urlparse(url).path.split("/")[-1]

    @staticmethod
    def get_id_from_internal_url(url: str) -> str:
        """Returns the internal id based on the given url."""
        return url.split(":")[-1]

    def __init__(self, query: Optional[str], key: Optional[int]) -> None:
        self.type = "spotify"
        super().__init__(query, key)

    def check_available(self) -> bool:
        if not self.gather_metadata():
            return False
        # the default bitrate of mopidy-spotify is 160kbps
        # estimate the size of a song by multiplying with its duration
        size = self.metadata["duration"] * 160 / 8 * 1000
        return self.check_not_too_large(size)

    def gather_metadata(self) -> bool:
        """Fetches metadata for this song's uri from Spotify."""
        if not self.id:
            results = self.api.search(self.query, type="track")

            result = self.first_unfiltered_item(
                results["tracks"]["items"],
                lambda item: (item["artists"][0]["name"], item["name"]),
            )
            if not result:
                return False
            self.id = result["id"]
        else:
            result = self.api.track(self.id)
        assert result
        try:
            self.metadata["artist"] = result["artists"][0]["name"]
            self.metadata["title"] = result["name"]
            self.metadata["duration"] = result["duration_ms"] / 1000
            self.metadata["internal_url"] = result["uri"]
            self.metadata["external_url"] = result["external_urls"]["spotify"]
            self.metadata["stream_url"] = None
            self.metadata["cached"] = False
        except KeyError:
            self.error = "No song found"
            return False
        return True

    def get_internal_url(self) -> str:
        if not self.id:
            raise ValueError()
        return "spotify:track:" + self.id

    def get_external_url(self) -> str:
        if not self.id:
            raise ValueError()
        return "https://open.spotify.com/track/" + self.id

    def get_suggestion(self) -> str:
        result = self.api.recommendations(limit=1, seed_tracks=[self.id])

        try:
            external_url = result["tracks"][0]["external_urls"]["spotify"]
        except (IndexError, KeyError) as error:
            self.error = "no recommendation found"
            raise ValueError("No suggested track") from error

        return external_url

    def request_radio(self, session_key: str) -> HttpResponse:
        result = self.api.recommendations(
            limit=storage.get("max_playlist_items"), seed_tracks=[self.id]
        )

        for track in result["tracks"]:
            external_url = track["external_urls"]["spotify"]
            provider = SpotifySongProvider(external_url, None)
            provider.request("", archive=False, manually_requested=False)

        return HttpResponse("queueing radio")


class SpotifyPlaylistProvider(PlaylistProvider, Spotify):
    """This class handles Spotify Playlists."""

    @staticmethod
    def get_id_from_external_url(url: str) -> Optional[str]:
        if not (
            url.startswith("https://open.spotify.com/playlist/")
            or url.startswith("https://open.spotify.com/artist/")
            or url.startswith("https://open.spotify.com/album/")
        ):
            return None
        return urlparse(url).path.split("/")[-1]

    def __init__(self, query: Optional[str], key: Optional[int]) -> None:
        self.type = "spotify"
        # can be one of playlists, artists or albums
        # defaults to playlist, only changes if an artist or album is found during search_id
        # this type is not reflected in list_id. Thus, ArchivedPlaylist entries do not know
        # what kind of collection of songs they are.
        # This is considered acceptable, generating external urls from playlist is never required
        # and finding cached lists still works as extracted ids still match
        self._spotify_type = "playlist"
        if query:
            if query.startswith("https://open.spotify.com/playlist/"):
                self._spotify_type = "playlist"
            elif query.startswith("https://open.spotify.com/artist/"):
                self._spotify_type = "artist"
            elif query.startswith("https://open.spotify.com/album/"):
                self._spotify_type = "album"
            super().__init__(query, key)

    def search_id(self) -> Optional[str]:
        result = self.api.search(self.query, limit=1, type="album,artist,playlist")

        try:
            list_info = result["albums"]["items"][0]
            self._spotify_type = "album"
        except IndexError:
            try:
                list_info = result["artists"]["items"][0]
                self._spotify_type = "artist"
            except IndexError:
                try:
                    list_info = result["playlists"]["items"][0]
                    self._spotify_type = "playlist"
                except IndexError:
                    self.error = "No playlist found"
                    return None

        list_id = list_info["id"]
        self.title = list_info["name"]

        return list_id

    def fetch_metadata(self) -> bool:
        if self.title is None:
            if self._spotify_type == "playlist":
                result = self.api.playlist(self.id, fields="name")
            elif self._spotify_type == "artist":
                result = self.api.artist(self.id, fields="name")
            elif self._spotify_type == "album":
                result = self.api.album(self.id, fields="name")
            else:
                assert False
            self.title = result["name"]

        # download at most 50 tracks for a playlist (spotifys maximum)
        # for more tracks paging would need to be implemented
        if self._spotify_type == "playlist":
            result = self.api.playlist_tracks(
                self.id,
                fields="items(track(external_urls(spotify)))",
                limit=storage.get("max_playlist_items"),
            )
            track_infos = result["items"]
            for track_info in track_infos:
                try:
                    self.urls.append(track_info["track"]["external_urls"]["spotify"])
                except KeyError:
                    # skip songs that have no urls
                    pass
        elif self._spotify_type == "artist":
            result = self.api.artist_top_tracks(
                self.id, limit=storage.get("max_playlist_items")
            )
            tracks = result["tracks"]
            for track in tracks:
                self.urls.append(track["external_urls"]["spotify"])
        elif self._spotify_type == "album":
            result = self.api.album_tracks(
                self.id,
                fields="items(external_urls(spotify))",
                limit=storage.get("max_playlist_items"),
            )
            tracks = result["items"]
            for track in tracks:
                self.urls.append(track["external_urls"]["spotify"])

        return True
