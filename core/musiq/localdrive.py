"""This module handles sound files that are stored on the local drive of the system."""

from __future__ import annotations

import os
import random
from typing import Optional, TYPE_CHECKING

from django.http.response import HttpResponse
from watson import search as watson

from core.models import ArchivedPlaylist, PlaylistEntry, ArchivedSong
from core.musiq import song_utils
from core.musiq.song_provider import SongProvider
from core.musiq.playlist_provider import PlaylistProvider

if TYPE_CHECKING:
    from core.musiq.musiq import Musiq
    from core.musiq.song_utils import Metadata


class LocalSongProvider(SongProvider):
    """A class handling local files on the drive.
    If the library is at /home/pi/Music/ and SONGS_CACHE_DIR is at /home/pi/raveberry
    there will be a symlink /home/pi/raveberry/local_library to /home/pi/Music

    Example values for a file at /home/pi/Music/Artist/Title.mp3 are:
    id: Artist/Title.mp3
    external_url: local_library/Artist/Title.mp3
    internal_url: file:///home/pi/local_library/Artist/Title.mp3
    """

    @staticmethod
    def get_id_from_external_url(url: str) -> str:
        """Returns the id of a local song for a given url."""
        return url[len("local_library/") :]

    def __init__(
        self, musiq: "Musiq", query: Optional[str], key: Optional[int]
    ) -> None:
        self.type = "local"
        super().__init__(musiq, query, key)

    def check_cached(self) -> bool:
        if not self.id:
            return False
        return os.path.isfile(self._get_path())

    def check_available(self) -> bool:
        if not self.id:
            # use the query to search for the local song
            # use the same algorithm that also provides the suggestions
            local_songs = ArchivedSong.objects.filter(url__startswith="local_library/")
            try:
                result = watson.search(self.query, models=(local_songs,))[0]
            except IndexError:
                self.error = "No local song found"
                return False
            url = result.meta["url"]
            self.id = LocalSongProvider.get_id_from_external_url(url)
            if not os.path.isfile(self._get_path()):
                self.error = "No local song found"
                return False
            return True
        else:
            if not os.path.isfile(self._get_path()):
                # Local files can not be downloaded from the internet
                self.error = "Local file missing"
                return False
        return True

    def make_available(self) -> bool:
        if not self.id:
            self.error = "Local file could not be made available"
            return False
        return True

    def get_metadata(self) -> "Metadata":
        metadata = song_utils.get_metadata(self._get_path())

        metadata["internal_url"] = self.get_internal_url()
        metadata["external_url"] = self.get_external_url()
        if not metadata["title"]:
            metadata["title"] = metadata["external_url"]

        return metadata

    def _get_path(self) -> str:
        return song_utils.get_path(self.get_external_url())

    def get_internal_url(self) -> str:
        return "file://" + self._get_path()

    def get_external_url(self) -> str:
        return "local_library/" + self.id

    def _get_corresponding_playlist(self) -> ArchivedPlaylist:
        entries = PlaylistEntry.objects.filter(url=self.get_external_url())
        if not entries.exists():
            raise PlaylistEntry.DoesNotExist()
        # There should be only one playlist containing this song. If there are more, choose any
        index = random.randint(0, entries.count() - 1)
        entry = entries.all()[index]
        playlist = entry.playlist
        return playlist

    def get_suggestion(self) -> str:
        playlist = self._get_corresponding_playlist()
        entries = playlist.entries
        index = random.randint(0, entries.count() - 1)
        entry = entries.all()[index]
        return entry.url

    def request_radio(self, request_ip: str) -> HttpResponse:
        playlist = self._get_corresponding_playlist()
        self.musiq.do_request_music(
            request_ip,
            playlist.title,
            playlist.id,
            True,
            "local",
            archive=False,
            manually_requested=False,
        )
        return HttpResponse("queueing radio")


class LocalPlaylistProvider(PlaylistProvider):
    """This class handles locals Playlists.
    Can only be used if playlists were created in the settings."""

    @staticmethod
    def get_id_from_external_url(url: str) -> str:
        return url[len("local_library/") :]

    def __init__(
        self, musiq: "Musiq", query: Optional[str], key: Optional[int]
    ) -> None:
        self.type = "local"
        super().__init__(musiq, query, key)

    def search_id(self) -> None:
        self.error = "local playlists can not be downloaded"

    def is_radio(self) -> bool:
        return False

    def fetch_metadata(self) -> bool:
        return True
