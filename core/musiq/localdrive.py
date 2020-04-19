"""This module handles sound files that are stored on the local drive of the system."""

import random

from core.models import PlaylistEntry
from core.musiq import song_utils
from core.musiq.music_provider import SongProvider, PlaylistProvider


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
    def get_id_from_external_url(url):
        """Returns the id of a local song for a given url."""
        return url[len("local_library/") :]

    def __init__(self, musiq, query, key):
        super().__init__(musiq, query, key)
        self.type = "local"

    def check_downloadable(self):
        # Local files can not be downloaded from the internet
        self.error = "Local file missing"
        return False

    def get_metadata(self):
        metadata = song_utils.get_metadata(self._get_path())

        metadata["internal_url"] = self.get_internal_url()
        metadata["external_url"] = self.get_external_url()
        if not metadata["title"]:
            metadata["title"] = metadata["external_url"]

        return metadata

    def _get_path(self):
        return song_utils.get_path(self.get_external_url())

    def get_internal_url(self):
        return "file://" + self._get_path()

    def get_external_url(self):
        return "local_library/" + self.id

    def _get_corresponding_playlist(self):
        entries = PlaylistEntry.objects.filter(url=self.get_external_url())
        if not entries.exists():
            raise PlaylistEntry.DoesNotExist()
        # There should be only one playlist containing this song. If there are more, choose any
        index = random.randint(0, entries.count() - 1)
        entry = entries.all()[index]
        playlist = entry.playlist
        return playlist

    def get_suggestion(self):
        playlist = self._get_corresponding_playlist()
        entries = playlist.entries
        index = random.randint(0, entries.count() - 1)
        entry = entries.all()[index]
        return entry.url

    def request_radio(self, request_ip):
        playlist = self._get_corresponding_playlist()
        return self.musiq.do_request_music(
            request_ip,
            playlist.title,
            playlist.id,
            True,
            "local",
            archive=False,
            manually_requested=False,
        )


class LocalPlaylistProvider(PlaylistProvider):
    """This class handles locals Playlists.
    Can only be used if playlists were created in the settings."""

    @staticmethod
    def get_id_from_external_url(url):
        return url[len("local_library/") :]

    def __init__(self, musiq, query, key):
        super().__init__(musiq, query, key)
        self.type = "local"

    def search_id(self):
        self.error = "local playlists can not be downloaded"

    def is_radio(self):
        return False

    def fetch_metadata(self):
        pass
