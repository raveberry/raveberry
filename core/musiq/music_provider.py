"""This module contains the base classes for all music providers."""
import os
import time

from django.conf import settings
from django.db import transaction
from django.db.models import F

import core.musiq.song_utils as song_utils
from core.models import (
    ArchivedSong,
    ArchivedQuery,
    ArchivedPlaylist,
    ArchivedPlaylistQuery,
    PlaylistEntry,
)
from core.models import RequestLog
from core.util import background_thread


class MusicProvider:
    """The base class for all music providers.
    Provides abstract function declarations."""

    def __init__(self, musiq, query, key):
        self.musiq = musiq
        self.query = query
        self.key = key
        self.id = None
        self.type = "unknown"
        self.placeholder = None
        self.error = "error"

    def check_cached(self):
        """Returns whether this resource is available on disk.
        Also sets the id of this resource."""
        raise NotImplementedError()

    def check_downloadable(self):
        """Returns whether this resource is available for download online."""
        raise NotImplementedError()

    def download(
        self, request_ip, background=True, archive=True, manually_requested=True
    ):
        """Downloads this resource and enqueues it afterwards."""
        raise NotImplementedError()

    def enqueue(self, request_ip, archive=True, manually_requested=True):
        """Adds the resource to the song queue."""
        raise NotImplementedError()


class SongProvider(MusicProvider):
    """The base class for all single song providers."""

    @staticmethod
    def get_id_from_external_url(url):
        """Constructs and returns the external id based on the given url."""
        raise NotImplementedError()

    @staticmethod
    def create(musiq, query=None, key=None, external_url=None):
        """Factory method to create a song provider.
        Either (query and key) or external url need to be specified.
        Detects the type of provider needed and returns one of corresponding type."""
        if key is not None:
            if query is None:
                musiq.base.logger.error("archived song requested but no query given")
                return None
            try:
                archived_song = ArchivedSong.objects.get(id=key)
            except ArchivedSong.DoesNotExist:
                musiq.base.logger.error("archived song requested for nonexistent key")
                return None
            external_url = archived_song.url
        if external_url.startswith("local_library/"):
            from core.musiq.localdrive import LocalSongProvider

            provider_class = LocalSongProvider
        elif external_url.startswith("https://www.youtube.com/"):
            from core.musiq.youtube import YoutubeSongProvider

            provider_class = YoutubeSongProvider
        elif external_url.startswith("https://open.spotify.com/"):
            from core.musiq.spotify import SpotifySongProvider

            provider_class = SpotifySongProvider
        else:
            raise NotImplementedError(f"No provider for given song: {external_url}")
        provider = provider_class(musiq, query, key)
        provider.id = provider_class.get_id_from_external_url(external_url)
        return provider

    def __init__(self, musiq, query, key):
        super().__init__(musiq, query, key)
        self.ok_message = "song queued"

        if key is None:
            self.archived = False
        else:
            self.archived = True

    def _get_path(self):
        raise NotImplementedError()

    def get_internal_url(self):
        """Returns the internal url based on this object's id."""
        raise NotImplementedError()

    def get_external_url(self):
        """Returns the external url based on this object's id."""
        raise NotImplementedError()

    def _check_cached(self):
        if self.id is not None:
            try:
                archived_song = ArchivedSong.objects.get(url=self.get_external_url())
            except ArchivedSong.DoesNotExist:
                return False
        elif self.key is not None:
            archived_song = ArchivedSong.objects.get(id=self.key)
        else:
            try:
                archived_song = ArchivedSong.objects.get(url=self.query)
            except ArchivedSong.DoesNotExist:
                return False
        self.id = self.__class__.get_id_from_external_url(archived_song.url)
        return True

    def check_cached(self):
        if not self._check_cached():
            return False
        return os.path.isfile(self._get_path())

    def check_downloadable(self):
        raise NotImplementedError()

    def enqueue(self, request_ip, archive=True, manually_requested=True):
        from core.musiq.player import Player

        metadata = self.get_metadata()

        # Increase counter of song/playlist
        with transaction.atomic():
            queryset = ArchivedSong.objects.filter(url=metadata["external_url"])
            if queryset.count() == 0:
                initial_counter = 1 if archive else 0
                archived_song = ArchivedSong.objects.create(
                    url=metadata["external_url"],
                    artist=metadata["artist"],
                    title=metadata["title"],
                    counter=initial_counter,
                )
            else:
                if archive:
                    queryset.update(counter=F("counter") + 1)
                archived_song = queryset.get()

            if archive:
                ArchivedQuery.objects.get_or_create(
                    song=archived_song, query=self.query
                )

        if archive and request_ip:
            RequestLog.objects.create(song=archived_song, address=request_ip)

        song = self.musiq.queue.enqueue(metadata, manually_requested)
        if self.placeholder:
            self.placeholder["replaced_by"] = song.id
        self.musiq.update_state()
        Player.queue_semaphore.release()

    def download(
        self, request_ip, background=True, archive=True, manually_requested=True
    ):
        self.enqueue(request_ip, archive=archive, manually_requested=manually_requested)

    def get_suggestion(self):
        """Returns the external url of a suggested song based on this one."""
        raise NotImplementedError()

    def get_metadata(self):
        """Returns a dictionary of this song's metadata."""
        raise NotImplementedError()

    def request_radio(self, request_ip):
        """Enqueues a playlist of songs based on this one."""
        raise NotImplementedError()


class PlaylistProvider(MusicProvider):
    """The base class for playlist providers."""

    @staticmethod
    def create(musiq, query=None, key=None):
        """Factory method to create a playlist provider.
        Both query and key need to be specified.
        Detects the type of provider needed and returns one of corresponding type."""
        if query is None:
            musiq.base.logger.error("archived playlist requested but no query given")
            return None
        try:
            archived_playlist = ArchivedPlaylist.objects.get(id=key)
        except ArchivedPlaylist.DoesNotExist:
            musiq.base.logger.error("archived song requested for nonexistent key")
            return None

        playlist_type = song_utils.determine_playlist_type(archived_playlist)
        if playlist_type == "local":
            from core.musiq.localdrive import LocalPlaylistProvider

            provider_class = LocalPlaylistProvider
        elif playlist_type == "youtube":
            from core.musiq.youtube import YoutubePlaylistProvider

            provider_class = YoutubePlaylistProvider
        elif playlist_type == "spotify":
            from core.musiq.spotify import SpotifyPlaylistProvider

            provider_class = SpotifyPlaylistProvider
        else:
            raise NotImplementedError(f"No provider for given playlist: {query}, {key}")
        provider = provider_class(musiq, query, key)
        return provider

    @staticmethod
    def get_id_from_external_url(url):
        """Constructs and returns the external id based on the given url."""
        raise NotImplementedError()

    def __init__(self, musiq, query, key):
        super().__init__(musiq, query, key)
        self.ok_message = "queueing playlist"
        self.title = None
        self.urls = []

    def check_cached(self):
        if self.key is not None:
            archived_playlist = ArchivedPlaylist.objects.get(id=self.key)
        else:
            try:
                list_id = self.get_id_from_external_url(self.query)
                archived_playlist = ArchivedPlaylist.objects.get(list_id=list_id)
            except (KeyError, ArchivedPlaylist.DoesNotExist):
                return False
        self.id = archived_playlist.list_id
        self.key = archived_playlist.id
        return True

    def search_id(self):
        """this a docstring."""
        raise NotImplementedError()

    def check_downloadable(self):
        list_id = self.get_id_from_external_url(self.query)
        if list_id is None:
            list_id = self.search_id()
        if list_id is None:
            return False
        self.id = list_id
        return True

    def is_radio(self):
        """Returns whether this playlist is a radio.
        A radio as a playlist that was created for a given song.
        The result can be different if called another time for the same song."""
        raise NotImplementedError()

    def fetch_metadata(self):
        """Fetches the title and list of songs for this playlist from the internet."""
        raise NotImplementedError()

    def download(
        self, request_ip, background=True, archive=True, manually_requested=True
    ):
        queryset = ArchivedPlaylist.objects.filter(list_id=self.id)
        if not self.is_radio() and queryset.exists():
            self.key = queryset.get().id
        else:
            self.fetch_metadata()
        self.enqueue(request_ip)
        return True

    @background_thread
    def _queue_songs(self, request_ip, archived_playlist):
        for index, entry in enumerate(archived_playlist.entries.all()):
            if index == self.musiq.base.settings.max_playlist_items:
                break
            # request every url in the playlist as their own url
            song_provider = SongProvider.create(self.musiq, external_url=entry.url)
            song_provider.query = entry.url

            if not song_provider.check_cached():
                if not song_provider.check_downloadable():
                    # song is not downloadable, continue with next song in playlist
                    continue
                if not song_provider.download(
                    request_ip,
                    background=False,
                    archive=False,
                    manually_requested=False,
                ):
                    # error during song download, continue with next song in playlist
                    continue
            else:
                song_provider.enqueue("", archive=False, manually_requested=False)

            if settings.DEBUG:
                # the sqlite database has problems if songs are pushed very fast
                # while a new song is taken from the queue. Add a delay to mitigate.
                time.sleep(1)

    def enqueue(self, request_ip, archive=True, manually_requested=True):
        if self.key is None:
            with transaction.atomic():

                archived_playlist = ArchivedPlaylist.objects.create(
                    list_id=self.id, title=self.title, counter=1
                )
                for index, url in enumerate(self.urls):
                    PlaylistEntry.objects.create(
                        playlist=archived_playlist, index=index, url=url,
                    )
        else:
            assert not self.is_radio()
            queryset = ArchivedPlaylist.objects.filter(list_id=self.id)

            if archive:
                queryset.update(counter=F("counter") + 1)
            archived_playlist = queryset.get()

        ArchivedPlaylistQuery.objects.get_or_create(
            playlist=archived_playlist, query=self.query
        )

        if self.musiq.base.settings.logging_enabled:
            RequestLog.objects.create(playlist=archived_playlist, address=request_ip)

        self._queue_songs(request_ip, archived_playlist)
