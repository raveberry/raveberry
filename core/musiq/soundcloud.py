"""This module contains all Soundcloud related code."""

from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING

import requests
import soundcloud
from bs4 import BeautifulSoup
from django.http.response import HttpResponse

from core.musiq import song_utils
from core.musiq.song_provider import SongProvider
from core.musiq.playlist_provider import PlaylistProvider

if TYPE_CHECKING:
    from core.musiq.musiq import Musiq
    from core.musiq.song_utils import Metadata


class Soundcloud:
    """This class contains code for both the song and playlist provider"""

    _web_client: soundcloud.Client.Client = None  # type: ignore

    @staticmethod
    def _get_web_client() -> soundcloud.Client.Client:
        if Soundcloud._web_client is None:
            Soundcloud._web_client = soundcloud.Client(
                client_id="93e33e327fd8a9b77becd179652272e2"
            )
        return Soundcloud._web_client

    @property
    def web_client(self) -> soundcloud.Client.Client:
        """Returns the web client if it was already created.
        If not, it is created using the client-id from mopidy-soundcloud."""
        return Soundcloud._get_web_client()

    def get_search_suggestions(self, musiq: Musiq, query: str) -> List[str]:
        """Returns a list of suggested items for the given query."""

        response = self.web_client.get(
            f"https://api-v2.soundcloud.com/search/queries", q=query
        )

        suggestions = [
            item.query
            for item in response.collection
            if not song_utils.is_forbidden(musiq, item.query)
        ]
        return suggestions


class SoundcloudSongProvider(SongProvider, Soundcloud):
    """This class handles songs from Soundcloud."""

    @staticmethod
    def get_id_from_external_url(url: str) -> str:
        track = Soundcloud._get_web_client().get("/resolve", url=url)
        return track.id

    @staticmethod
    def get_id_from_internal_url(url: str) -> str:
        """Returns the internal id based on the given url."""
        return url.split(".")[-1]

    def __init__(
        self, musiq: "Musiq", query: Optional[str], key: Optional[int]
    ) -> None:
        self.type = "soundcloud"
        super().__init__(musiq, query, key)

        self.metadata: "Metadata" = {}
        self.external_url = None

    def check_cached(self) -> bool:
        # Soundcloud songs cannot be cached and have to be streamed everytime
        return False

    def check_available(self) -> bool:
        return self.gather_metadata()

    # track_info is of type mopidy.models.Track, but mopidy should not be a dependency, so no import
    def gather_metadata(self) -> bool:
        """Fetches metadata for this song's uri from Soundcloud."""
        if not self.id:
            results = self.web_client.get("/tracks", q=self.query, limit=20)

            # apply the filterlist from the settings
            for item in results:
                artist = item.user["username"]
                title = item.title
                if song_utils.is_forbidden(
                    self.musiq, artist
                ) or song_utils.is_forbidden(self.musiq, title):
                    continue
                result = item
                break
            else:
                # all tracks got filtered
                return False
            self.id = result.id
        else:
            result = self.web_client.get(f"tracks/{self.id}")
        self.metadata["internal_url"] = self.get_internal_url()
        self.metadata["external_url"] = result.permalink_url
        self.metadata["artist"] = result.user["username"]
        self.metadata["title"] = result.title
        self.metadata["duration"] = result.duration / 1000
        return True

    def get_metadata(self) -> "Metadata":
        if not self.metadata:
            self.gather_metadata()
        return self.metadata

    def _get_path(self) -> str:
        # soundcloud is not cached in the cache directory
        raise NotImplementedError()

    def get_internal_url(self) -> str:
        if not self.id:
            raise ValueError()
        return f"soundcloud:song.{self.id}"

    def get_external_url(self) -> str:
        if not self.id:
            raise ValueError()
        return self.get_metadata()["external_url"]

    def _get_related_urls(self) -> List[str]:
        response = requests.get(self.get_external_url() + "/recommended")

        soup = BeautifulSoup(response.text, "html.parser")

        # the first article is the current one
        articles = soup.select("article")[1:]
        urls = [
            "https://soundcloud.com" + article.select_one("a")["href"]
            for article in articles
        ]
        return urls

    def get_suggestion(self) -> str:
        return self._get_related_urls()[0]

    def request_radio(self, request_ip: str) -> HttpResponse:
        urls = self._get_related_urls()

        for external_url in urls:
            self.musiq.do_request_music(
                "",
                external_url,
                None,
                False,
                "soundcloud",
                archive=False,
                manually_requested=False,
            )

        return HttpResponse("queueing radio")


class SoundcloudPlaylistProvider(PlaylistProvider, Soundcloud):
    """This class handles Soundcloud Playlists."""

    @staticmethod
    def get_id_from_external_url(url: str) -> Optional[str]:
        if not url.startswith("https://soundcloud.com/"):
            return None
        playlist = Soundcloud._get_web_client().get("/resolve", url=url)
        return playlist.id

    def __init__(
        self, musiq: "Musiq", query: Optional[str], key: Optional[int]
    ) -> None:
        self.type = "soundcloud"
        super().__init__(musiq, query, key)

    def search_id(self) -> Optional[str]:
        results = self.web_client.get("/playlists", q=self.query, limit=1)

        try:
            playlist = results[0]
        except IndexError:
            self.error = "No playlist found"
            return None

        list_id = playlist.id
        self.title = playlist.title

        return list_id

    def is_radio(self) -> bool:
        return False

    def fetch_metadata(self) -> bool:
        if self.title is None:
            result = self.web_client.get(f"/playlists/{self.id}")
            self.title = result.name

        tracks = self.web_client.get(f"/playlists/{self.id}/tracks")

        for track in tracks:
            self.urls.append(track.permalink_url)

        return True
