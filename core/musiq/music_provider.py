"""This module contains the base classes for all music providers."""

from __future__ import annotations

import logging
import os
import time

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse

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
from typing import Optional, Union, Dict, TYPE_CHECKING, Type, List, cast

if TYPE_CHECKING:
    from core.musiq.musiq import Musiq
    from core.musiq.song_utils import Metadata


class WrongUrlError(Exception):
    pass


class MusicProvider:
    """The base class for all music providers.
    Provides abstract function declarations."""

    def __init__(
        self, musiq: "Musiq", query: Optional[str], key: Optional[int]
    ) -> None:
        self.musiq = musiq
        self.query = query
        self.key = key
        if not hasattr(self, "type"):
            # the type should already have been set by the base class
            self.type = "unknown"
            assert False
        self.id: Optional[str] = self.extract_id()
        self.placeholder: Optional[Dict[str, Union[Optional[int], str]]] = None
        self.ok_message = "ok"
        self.error = "error"

    def extract_id(self):
        """Tries to extract the id from the given query.
        Returns the id if possible, otherwise None"""
        return None

    def check_cached(self) -> bool:
        """Returns whether this resource is available on disk."""
        raise NotImplementedError()

    def check_downloadable(self) -> bool:
        """Returns whether this resource is available for download online."""
        raise NotImplementedError()

    def download(
        self,
        request_ip: str,
        background: bool = True,
        archive: bool = True,
        manually_requested: bool = True,
    ) -> bool:
        """Downloads this resource and enqueues it afterwards."""
        raise NotImplementedError()

    def enqueue(
        self, request_ip: str, archive: bool = True, manually_requested: bool = True
    ):
        """Adds the resource to the song queue."""
        raise NotImplementedError()


class SongProvider(MusicProvider):
    """The base class for all single song providers."""

    @staticmethod
    def get_id_from_external_url(url: str) -> str:
        """Constructs and returns the external id based on the given url."""
        raise NotImplementedError()

    @staticmethod
    def create(
        musiq: "Musiq",
        query: Optional[str] = None,
        key: Optional[int] = None,
        external_url: Optional[str] = None,
    ) -> SongProvider:
        """Factory method to create a song provider.
        Either (query and key) or external url need to be specified.
        Detects the type of provider needed and returns one of corresponding type."""
        if key is not None:
            if query is None:
                logging.error(f"archived song requested but no query given (key {key})")
                raise ValueError()
            try:
                archived_song = ArchivedSong.objects.get(id=key)
            except ArchivedSong.DoesNotExist:
                logging.error(f"archived song requested for nonexistent key {key}")
                raise ValueError()
            external_url = archived_song.url
        if external_url is None:
            raise ValueError(
                "external_url was provided and could not be inferred from remaining attributes."
            )
        provider_class: Optional[Type[SongProvider]] = None
        url_type = song_utils.determine_url_type(external_url)
        if url_type == "local":
            from core.musiq.localdrive import LocalSongProvider

            provider_class = LocalSongProvider
        elif url_type == "youtube":
            from core.musiq.youtube import YoutubeSongProvider

            provider_class = YoutubeSongProvider
        elif url_type == "spotify":
            from core.musiq.spotify import SpotifySongProvider

            provider_class = SpotifySongProvider
        elif url_type == "soundcloud":
            from core.musiq.soundcloud import SoundcloudSongProvider

            provider_class = SoundcloudSongProvider
        if not provider_class:
            raise NotImplementedError(f"No provider for given song: {external_url}")
        if not query and external_url:
            query = external_url
        provider = provider_class(musiq, query, key)
        return provider

    def __init__(
        self, musiq: "Musiq", query: Optional[str], key: Optional[int]
    ) -> None:
        super().__init__(musiq, query, key)
        self.ok_message = "song queued"

        if query:
            url_type = song_utils.determine_url_type(query)
            if url_type != self.type and url_type != "unknown":
                raise WrongUrlError(
                    f"Tried to create a {self.type} provider with: {query}"
                )

    def _get_path(self) -> str:
        raise NotImplementedError()

    def get_internal_url(self) -> str:
        """Returns the internal url based on this object's id."""
        raise NotImplementedError()

    def get_external_url(self) -> str:
        """Returns the external url based on this object's id."""
        raise NotImplementedError()

    def extract_id(self) -> Optional[str]:
        if self.key is not None:
            try:
                archived_song = ArchivedSong.objects.get(id=self.key)
                return self.__class__.get_id_from_external_url(archived_song.url)
            except ArchivedSong.DoesNotExist:
                return None
        if self.query is not None:
            url_type = song_utils.determine_url_type(self.query)
            if url_type == "youtube":
                from core.musiq.youtube import YoutubeSongProvider

                return YoutubeSongProvider.get_id_from_external_url(self.query)
            elif url_type == "spotify":
                from core.musiq.spotify import SpotifySongProvider

                return SpotifySongProvider.get_id_from_external_url(self.query)
            elif url_type == "soundcloud":
                from core.musiq.soundcloud import SoundcloudSongProvider

                return SoundcloudSongProvider.get_id_from_external_url(self.query)
            # interpret the query as an external url and try to look it up in the database
            try:
                archived_song = ArchivedSong.objects.get(url=self.query)
                return self.__class__.get_id_from_external_url(archived_song.url)
            except ArchivedSong.DoesNotExist:
                return None
        assert False

    def check_downloadable(self) -> bool:
        raise NotImplementedError()

    def enqueue(
        self, request_ip: str, archive: bool = True, manually_requested: bool = True
    ) -> None:
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
        self,
        request_ip: str,
        background: bool = True,
        archive: bool = True,
        manually_requested: bool = True,
    ) -> bool:
        # self.enqueue(request_ip, archive=archive, manually_requested=manually_requested)
        raise NotImplementedError()

    def get_suggestion(self) -> str:
        """Returns the external url of a suggested song based on this one."""
        raise NotImplementedError()

    def get_metadata(self) -> "Metadata":
        """Returns a dictionary of this song's metadata."""
        raise NotImplementedError()

    def request_radio(self, request_ip) -> HttpResponse:
        """Enqueues a playlist of songs based on this one."""
        raise NotImplementedError()


class PlaylistProvider(MusicProvider):
    """The base class for playlist providers."""

    @staticmethod
    def create(
        musiq: "Musiq", query: Optional[str] = None, key: Optional[int] = None,
    ) -> PlaylistProvider:
        """Factory method to create a playlist provider.
        Both query and key need to be specified.
        Detects the type of provider needed and returns one of corresponding type."""
        if query is None:
            logging.error(f"archived playlist requested but no query given (key {key})")
            raise ValueError
        if key is None:
            logging.error("archived playlist requested but no key given")
            raise ValueError
        try:
            archived_playlist = ArchivedPlaylist.objects.get(id=key)
        except ArchivedPlaylist.DoesNotExist:
            logging.error(f"archived song requested for nonexistent key {key}")
            raise ValueError

        playlist_type = song_utils.determine_playlist_type(archived_playlist)
        provider_class: Optional[Type[PlaylistProvider]] = None
        if playlist_type == "local":
            from core.musiq.localdrive import LocalPlaylistProvider

            provider_class = LocalPlaylistProvider
        elif playlist_type == "youtube":
            from core.musiq.youtube import YoutubePlaylistProvider

            provider_class = YoutubePlaylistProvider
        elif playlist_type == "spotify":
            from core.musiq.spotify import SpotifyPlaylistProvider

            provider_class = SpotifyPlaylistProvider
        elif playlist_type == "soundcloud":
            from core.musiq.soundcloud import SoundcloudPlaylistProvider

            provider_class = SoundcloudPlaylistProvider
        if not provider_class:
            raise NotImplementedError(f"No provider for given playlist: {query}, {key}")
        provider = provider_class(musiq, query, key)
        return provider

    @staticmethod
    def get_id_from_external_url(url: str) -> Optional[str]:
        """Constructs and returns the external id based on the given url."""
        raise NotImplementedError()

    def __init__(
        self, musiq: "Musiq", query: Optional[str], key: Optional[int]
    ) -> None:
        super().__init__(musiq, query, key)
        self.ok_message = "queueing playlist"
        self.title: Optional[str] = None
        self.urls: List[str] = []

    def check_cached(self) -> bool:
        if self.key is not None:
            archived_playlist = ArchivedPlaylist.objects.get(id=self.key)
        else:
            assert self.query
            try:
                list_id = self.get_id_from_external_url(self.query)
                archived_playlist = ArchivedPlaylist.objects.get(list_id=list_id)
            except (KeyError, ArchivedPlaylist.DoesNotExist):
                return False
        self.id = archived_playlist.list_id
        self.key = archived_playlist.id
        return True

    def search_id(self) -> Optional[str]:
        """Fetches the id of this playlist from the internet and returns it."""
        raise NotImplementedError()

    def check_downloadable(self) -> bool:
        assert self.query
        list_id = self.get_id_from_external_url(self.query)
        if list_id is None:
            list_id = self.search_id()
        if list_id is None:
            return False
        self.id = list_id
        return True

    def is_radio(self) -> bool:
        """Returns whether this playlist is a radio.
        A radio as a playlist that was created for a given song.
        The result can be different if called another time for the same song."""
        raise NotImplementedError()

    def fetch_metadata(self) -> bool:
        """Fetches the title and list of songs for this playlist from the internet."""
        raise NotImplementedError()

    def download(
        self,
        request_ip: str,
        background: bool = True,
        archive: bool = True,
        manually_requested: bool = True,
    ) -> bool:
        queryset = ArchivedPlaylist.objects.filter(list_id=self.id)
        if not self.is_radio() and queryset.exists():
            self.key = queryset.get().id
        else:
            if not self.fetch_metadata():
                return False
        self.enqueue(request_ip)
        return True

    @background_thread
    def _queue_songs(
        self, request_ip: str, archived_playlist: ArchivedPlaylist
    ) -> None:
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
        if self.is_radio():
            # Delete radios after they were queued.
            # They are only stored in the database to ensure the correct queueing order.
            # Deleting the playlist deletes corresponding playlist entries and queries.
            archived_playlist.delete()

    def enqueue(
        self, request_ip: str, archive: bool = True, manually_requested: bool = True
    ) -> None:
        if self.key is None:
            assert self.id and self.title
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
