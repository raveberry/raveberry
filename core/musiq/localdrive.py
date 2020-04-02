import os
import random

from django.http import HttpResponseBadRequest

from core.models import PlaylistEntry
from core.musiq import song_utils
from core.musiq.music_provider import SongProvider, PlaylistProvider
from main import settings


class LocalSongProvider(SongProvider):
    """
    A class handling local files on the drive.
    If the library is at /home/pi/Music/ and SONGS_CACHE_DIR is at /home/pi/raveberry
    there will be a symlink /home/pi/raveberry/local_library to /home/pi/Music

    Example values for a file at /home/pi/Music/Artist/Title.mp3 are:
    id: Artist/Title.mp3
    external_url: local_library/Artist/Title.mp3
    internal_url: file:///home/pi/local_library/Artist/Title.mp3
    """

    @staticmethod
    def get_id_from_external_url(url):
        return url[len('local_library/'):]

    def __init__(self, musiq, query, key):
        super().__init__(musiq, query, key)
        self.type = 'local'

    def check_cached(self):
        if not self._check_cached():
            return False
        return os.path.isfile(self.get_path())

    def check_downloadable(self):
        # Local files can not be downloaded from the internet
        self.error = 'Local file missing'
        return False

    def get_metadata(self):
        metadata = song_utils.get_metadata(self.get_path())

        metadata['internal_url'] = self.get_internal_url()
        metadata['external_url'] = self.get_external_url()
        if not metadata['title']:
            metadata['title'] = metadata['external_url']

        return metadata

    def get_path(self):
        path = os.path.join(settings.SONGS_CACHE_DIR, self.get_external_url())
        path = path.replace('~', os.environ['HOME'])
        path = os.path.abspath(path)
        return path

    def get_internal_url(self):
        return 'file://' + self.get_path()

    def get_external_url(self):
        return 'local_library/' + self.id

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

    def request_radio(self, ip):
        playlist = self._get_corresponding_playlist()
        return self.musiq._request_music(ip, playlist.title, playlist.id, True, 'local', archive=False, manually_requested=False)

class LocalPlaylistProvider(PlaylistProvider):

    @staticmethod
    def get_id_from_external_url(url):
        return url[len('local_library/'):]

    def __init__(self, musiq, query, key):
        super().__init__(musiq, query, key)
        self.type = 'local'

    def search_id(self):
        self.error = 'local playlists can not be downloaded'
        return None

    def is_radio(self):
        return False
