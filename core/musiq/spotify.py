"""This module contains all Spotify related code."""

from __future__ import annotations

from urllib.parse import urlparse

from django.http import HttpResponse
from core.musiq.spotify_web import OAuthClient

from core.models import Setting
from core.musiq import song_utils
from core.musiq.music_provider import SongProvider, PlaylistProvider
from django.http.response import HttpResponse
from typing import Dict, Optional, Union, List, Tuple, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.musiq.musiq import Musiq
    from core.musiq.song_utils import Metadata
    from core.musiq.player import Player


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
        self, query: str, playlist: bool
    ) -> List[Tuple[str, str]]:
        """Returns a list of suggested items for the given query.
        Returns playlists if :param playlist: is True, songs otherwise."""
        result = self.web_client.get(
            "search",
            params={
                "q": query,
                "limit": "10",
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
                displayname = song_utils.displayname(artist, title)
            suggestions.append((displayname, external_url))

        # remove duplicates
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
        """Constructs and returns the internal id based on the given url."""
        return url.split(":")[-1]

    def __init__(
        self, musiq: "Musiq", query: Optional[str], key: Optional[int]
    ) -> None:
        super().__init__(musiq, query, key)

        if query and query.startswith("https://www.youtube.com/watch?v="):
            raise ValueError("Tried to create a Spotify provider using a Youtube Url")

        self.type = "spotify"
        self.spotify_library = musiq.player.player.library
        self.metadata: "Metadata" = {}

    def check_cached(self) -> bool:
        if self.query is not None and self.query.startswith(
            "https://open.spotify.com/"
        ):
            extracted_id = SpotifySongProvider.get_id_from_external_url(self.query)
            if extracted_id is not None:
                self.id = extracted_id

        if not super()._check_cached():
            return False
        # Spotify songs cannot be cached and have to be streamed everytime
        return False

    def check_downloadable(self) -> bool:
        if self.id is not None:
            return self.gather_metadata()

        results = self.spotify_library.search({"any": [self.query]})

        try:
            track_info = results[0].tracks[0]
        except IndexError:
            self.error = "Spotify not enabled in Mopidy"
            return False
        except AttributeError:
            self.error = "Song not found"
            return False
        self.id = SpotifySongProvider.get_id_from_internal_url(track_info.uri)
        self.gather_metadata(track_info=track_info)
        return True

    def download(
        self,
        request_ip: str,
        background: bool = True,
        archive: bool = True,
        manually_requested: bool = True,
    ) -> bool:
        self.enqueue(request_ip, archive=archive, manually_requested=manually_requested)
        # spotify need to be streamed, no download possible
        return True

    # track_info is of type mopidy.models.Track, but mopidy should not be a dependency, so no import
    def gather_metadata(self, track_info: Any = None) -> bool:
        """Fetches metadata for this song's uri from Spotify."""
        if not track_info:
            results = self.spotify_library.search({"uri": [self.get_internal_url()]})
            try:
                track_info = results[0].tracks[0]
            except IndexError:
                self.error = "Spotify not enabled in Mopidy"
                return False

        self.metadata["internal_url"] = track_info.uri
        self.metadata["external_url"] = self.get_external_url()
        self.metadata["artist"] = track_info.artists[0].name
        self.metadata["title"] = track_info.name
        self.metadata["duration"] = track_info.length / 1000
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
                "limit": self.musiq.base.settings.max_playlist_items,
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
        if not url.startswith("https://open.spotify.com/playlist/"):
            return None
        return urlparse(url).path.split("/")[-1]

    def __init__(
        self, musiq: "Musiq", query: Optional[str], key: Optional[int]
    ) -> None:
        super().__init__(musiq, query, key)
        self.type = "spotify"

    def search_id(self) -> Optional[str]:
        result = self.web_client.get(
            "search",
            params={
                "q": self.query,
                "limit": "1",
                "market": "from_token",
                "type": "playlist",
            },
        )

        try:
            list_info = result["playlists"]["items"][0]
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
                f"playlists/{self.id}", params={"fields": "name", "limit": "50"},
            )
            self.title = result["name"]

        # download at most 50 tracks for a playlist (spotifys maximum)
        # for more tracks paging would need to be implemented
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

        return True
