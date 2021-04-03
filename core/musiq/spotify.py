"""This module contains all Spotify related code."""

from __future__ import annotations

from typing import Optional, List, Tuple, TYPE_CHECKING
from urllib.parse import urlparse

from django.http.response import HttpResponse

from core.models import Setting
from core.musiq import song_utils
from core.musiq.song_provider import SongProvider
from core.musiq.playlist_provider import PlaylistProvider
from core.musiq.spotify_web import OAuthClient

if TYPE_CHECKING:
    from core.musiq.musiq import Musiq
    from core.musiq.song_utils import Metadata


class Spotify:
    """This class contains code for both the song and playlist provider"""

    _web_client: OAuthClient = None  # type: ignore

    @property
    def web_client(self) -> OAuthClient:
        """Returns the web client if it was already created.
        If not, it is created using the spotify credentials from the database."""
        if Spotify._web_client is None:
            client_id = Setting.objects.get(key="spotify_client_id").value
            client_secret = Setting.objects.get(key="spotify_client_secret").value
            Spotify._web_client = OAuthClient(
                base_url="https://api.spotify.com/v1",
                refresh_url="https://auth.mopidy.com/spotify/token",
                client_id=client_id,
                client_secret=client_secret,
            )
        return Spotify._web_client

    def get_search_suggestions(
        self, musiq: Musiq, query: str, playlist: bool
    ) -> List[Tuple[str, str]]:
        """Returns a list of suggested items for the given query.
        Returns playlists if :param playlist: is True, songs otherwise."""
        result = self.web_client.get(
            "search",
            params={
                "q": query,
                "limit": "20",
                "market": "from_token",
                "type": "playlist" if playlist else "track",
            },
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
                if song_utils.is_forbidden(musiq, artist) or song_utils.is_forbidden(
                    musiq, title
                ):
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

    def __init__(
        self, musiq: "Musiq", query: Optional[str], key: Optional[int]
    ) -> None:
        self.type = "spotify"
        super().__init__(musiq, query, key)

        self.metadata: "Metadata" = {}

    def check_cached(self) -> bool:
        # Spotify songs cannot be cached and have to be streamed everytime
        return False

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
            results = self.web_client.get(
                "search",
                params={
                    "q": self.query,
                    "limit": "50",
                    "market": "from_token",
                    "type": "track",
                },
            )

            # apply the filterlist from the settings
            for item in results["tracks"]["items"]:
                artist = item["artists"][0]["name"]
                title = item["name"]
                if song_utils.is_forbidden(
                    self.musiq, artist
                ) or song_utils.is_forbidden(self.musiq, title):
                    continue
                result = item
                break
            else:
                # all tracks got filtered
                self.error = "All results filtered"
                return False
        else:
            result = self.web_client.get(f"tracks/{self.id}", params={"limit": "1"})
        try:
            self.metadata["internal_url"] = result["uri"]
            self.metadata["external_url"] = result["external_urls"]["spotify"]
            self.metadata["artist"] = result["artists"][0]["name"]
            self.metadata["title"] = result["name"]
            self.metadata["duration"] = result["duration_ms"] / 1000
        except KeyError:
            self.error = "No song found"
            return False
        return True

    def get_metadata(self) -> "Metadata":
        if not self.metadata:
            self.gather_metadata()
        return self.metadata

    def _get_path(self) -> str:
        # spotify is not cached in the cache directory
        raise NotImplementedError()

    def get_internal_url(self) -> str:
        if not self.id:
            raise ValueError()
        return "spotify:track:" + self.id

    def get_external_url(self) -> str:
        if not self.id:
            raise ValueError()
        return "https://open.spotify.com/track/" + self.id

    def get_suggestion(self) -> str:
        result = self.web_client.get(
            "recommendations",
            params={"limit": "1", "market": "from_token", "seed_tracks": self.id},
        )

        try:
            external_url = result["tracks"][0]["external_urls"]["spotify"]
        except IndexError:
            self.error = "no recommendation found"
            raise ValueError("No suggested track")

        return external_url

    def request_radio(self, request_ip: str) -> HttpResponse:
        result = self.web_client.get(
            "recommendations",
            params={
                "limit": self.musiq.base.settings.basic.max_playlist_items,
                "market": "from_token",
                "seed_tracks": self.id,
            },
        )

        for track in result["tracks"]:
            external_url = track["external_urls"]["spotify"]
            self.musiq.do_request_music(
                "",
                external_url,
                None,
                False,
                "spotify",
                archive=False,
                manually_requested=False,
            )

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

    def __init__(
        self, musiq: "Musiq", query: Optional[str], key: Optional[int]
    ) -> None:
        self.type = "spotify"
        # can be one of playlists, artists or albums
        # defaults to playlist, only changes if an artist or album is found during search_id
        # this type is not reflected in list_id. Thus, ArchivedPlaylist entries do not know
        # what kind of collection of songs they are.
        # This is considered acceptable, generating external urls from playlist is never required
        # and finding cached lists still works as extracted ids still match
        self._spotify_endpoint = "playlists"
        if query:
            if query.startswith("https://open.spotify.com/playlist/"):
                self._spotify_endpoint = "playlists"
            elif query.startswith("https://open.spotify.com/artist/"):
                self._spotify_endpoint = "artists"
            elif query.startswith("https://open.spotify.com/album/"):
                self._spotify_endpoint = "albums"
            super().__init__(musiq, query, key)

    def search_id(self) -> Optional[str]:
        result = self.web_client.get(
            "search",
            params={
                "q": self.query,
                "limit": "1",
                "market": "from_token",
                "type": "artist,album,playlist",
            },
        )

        try:
            list_info = result["artists"]["items"][0]
            self._spotify_endpoint = "artists"
        except IndexError:
            try:
                list_info = result["albums"]["items"][0]
                self._spotify_endpoint = "albums"
            except IndexError:
                try:
                    list_info = result["playlists"]["items"][0]
                    self._spotify_endpoint = "playlists"
                except IndexError:
                    self.error = "No playlist found"
                    return None

        list_id = list_info["id"]
        self.title = list_info["name"]

        return list_id

    def is_radio(self) -> bool:
        return False

    def fetch_metadata(self) -> bool:
        if self.title is None:
            result = self.web_client.get(
                f"{self._spotify_endpoint}/{self.id}", params={"fields": "name"}
            )
            self.title = result["name"]

        # download at most 50 tracks for a playlist (spotifys maximum)
        # for more tracks paging would need to be implemented
        if self._spotify_endpoint == "playlists":
            result = self.web_client.get(
                f"playlists/{self.id}/tracks",
                params={
                    "fields": "items(track(external_urls(spotify)))",
                    "limit": "50",
                    "market": "from_token",
                },
            )
            track_infos = result["items"]
            for track_info in track_infos:
                self.urls.append(track_info["track"]["external_urls"]["spotify"])
        elif self._spotify_endpoint == "artists":
            result = self.web_client.get(
                f"artists/{self.id}/top-tracks",
                params={
                    "fields": "tracks(external_urls(spotify))",
                    "limit": "50",
                    "market": "from_token",
                },
            )
            tracks = result["tracks"]
            for track in tracks:
                self.urls.append(track["external_urls"]["spotify"])
        elif self._spotify_endpoint == "albums":
            result = self.web_client.get(
                f"albums/{self.id}/tracks",
                params={
                    "fields": "items(external_urls(spotify))",
                    "limit": "50",
                    "market": "from_token",
                },
            )
            tracks = result["items"]
            for track in tracks:
                self.urls.append(track["external_urls"]["spotify"])

        return True
