"""This module contains the base classes for all music providers."""

from __future__ import annotations

import logging
import time
from typing import Optional, TYPE_CHECKING, Type, List

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
    QueuedSong,
)
from core.models import RequestLog
from core.util import background_thread

if TYPE_CHECKING:
    from core.musiq.musiq import Musiq
    from core.musiq.song_utils import Metadata


class ProviderError(Exception):
    """An error to indicate that an error occurred while providing music."""


class WrongUrlError(Exception):
    """An error to indicate that a provider was called
    with a url that belongs to a different service."""


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
        self.ok_message = "ok"
        self.error = "error"

    def extract_id(self) -> Optional[str]:
        """Tries to extract the id from the given query.
        Returns the id if possible, otherwise None"""
        return None

    def check_cached(self) -> bool:
        """Returns whether this resource is available on disk."""
        raise NotImplementedError()

    def check_available(self) -> bool:
        """Returns whether this resource is available online."""
        raise NotImplementedError()

    def enqueue_placeholder(self, manually_requested) -> None:
        """Enqueues a placeholder if applicable. Playlists have no placeholder, only songs do.
        Used to identify this resource in the client after a request."""
        raise NotImplementedError()

    def remove_placeholder(self) -> None:
        """Removes the placeholder in the queue that represents this resource.
        Called if there was an error and this element needs to be removed from the queue."""
        raise NotImplementedError()

    def make_available(self) -> bool:
        """Makes this resource available for playback.
        If possible, downloads it to disk.
        If this takes a long time, calls update_state so the placeholder is visible.
        Returns False if an error occured, True otherwise."""
        raise NotImplementedError()

    def persist(self, request_ip: str, archive: bool = True) -> None:
        """Updates the database.
        Creates an archived entry or updates it.
        Also handles logging to database."""
        raise NotImplementedError()

    def enqueue(self) -> None:
        """Updates the placeholder in the song queue with the actual data."""
        raise NotImplementedError()

    def request(
        self, request_ip: str, archive: bool = True, manually_requested: bool = True,
    ) -> None:
        """Tries to request this resource.
        Uses the local cache if possible, otherwise tries to retrieve it online."""

        def enqueue() -> None:
            self.persist(request_ip, archive=archive)
            self.enqueue()

        enqueue_function = enqueue

        if not self.check_cached():
            if not self.check_available():
                raise ProviderError()

            # overwrite the enqueue function and make the resource available before calling it
            def fetch_enqueue() -> None:
                if not self.make_available():
                    self.remove_placeholder()
                    self.musiq.update_state()
                    return

                enqueue()

            enqueue_function = fetch_enqueue

        if self.musiq.base.settings.basic.new_music_only and isinstance(
            self, SongProvider
        ):
            try:
                archived_song = ArchivedSong.objects.get(url=self.get_external_url())
                if archived_song.counter > 0:
                    self.error = "Only new music is allowed!"
                    raise ProviderError()
            except ArchivedSong.DoesNotExist:
                pass

        self.enqueue_placeholder(manually_requested)

        @background_thread
        def enqueue_in_background() -> None:
            enqueue_function()

        enqueue_in_background()


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
                logging.error(
                    "archived song requested but no query given (key %s)", key
                )
                raise ValueError()
            try:
                archived_song = ArchivedSong.objects.get(id=key)
            except ArchivedSong.DoesNotExist:
                logging.error("archived song requested for nonexistent key %s", key)
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
        self.queued_song: Optional[QueuedSong] = None

        if query:
            url_type = song_utils.determine_url_type(query)
            if url_type not in (self.type, "unknown"):
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
            if url_type == "spotify":
                from core.musiq.spotify import SpotifySongProvider

                return SpotifySongProvider.get_id_from_external_url(self.query)
            if url_type == "soundcloud":
                from core.musiq.soundcloud import SoundcloudSongProvider

                return SoundcloudSongProvider.get_id_from_external_url(self.query)
            # interpret the query as an external url and try to look it up in the database
            try:
                archived_song = ArchivedSong.objects.get(url=self.query)
                return self.__class__.get_id_from_external_url(archived_song.url)
            except ArchivedSong.DoesNotExist:
                return None
        logging.error("Can not extract id because neither key nor query are known")
        return None

    def enqueue_placeholder(self, manually_requested) -> None:
        metadata: Metadata = {
            "internal_url": "",
            "external_url": "",
            "artist": "",
            "title": self.query or self.get_external_url(),
            "duration": -1,
        }
        initial_votes = 1 if manually_requested else 0
        self.queued_song = self.musiq.queue.enqueue(
            metadata, manually_requested, votes=initial_votes
        )

    def remove_placeholder(self) -> None:
        assert self.queued_song
        self.queued_song.delete()

    def check_available(self) -> bool:
        raise NotImplementedError()

    def make_available(self) -> bool:
        return True

    def persist(self, request_ip: str, archive: bool = True) -> None:
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

        if self.musiq.base.settings.basic.logging_enabled and request_ip:
            RequestLog.objects.create(song=archived_song, address=request_ip)

    def enqueue(self) -> None:
        assert self.queued_song
        if not self.musiq.queue.filter(id=self.queued_song.id).exists():
            # this song was already deleted, do not enqueue
            return

        from core.musiq.playback import Playback

        metadata = self.get_metadata()

        self.queued_song.internal_url = metadata["internal_url"]
        self.queued_song.external_url = metadata["external_url"]
        self.queued_song.artist = metadata["artist"]
        self.queued_song.title = metadata["title"]
        self.queued_song.duration = metadata["duration"]
        # make sure not to overwrite the index as it may have changed in the meantime
        self.queued_song.save(
            update_fields=[
                "internal_url",
                "external_url",
                "artist",
                "title",
                "duration",
            ]
        )

        self.musiq.update_state()
        Playback.queue_semaphore.release()

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
            logging.error(
                "archived playlist requested but no query given (key %s)", key
            )
            raise ValueError
        if key is None:
            logging.error("archived playlist requested but no key given")
            raise ValueError
        try:
            archived_playlist = ArchivedPlaylist.objects.get(id=key)
        except ArchivedPlaylist.DoesNotExist:
            logging.error("archived song requested for nonexistent key %s", key)
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
            assert self.query is not None
            try:
                list_id = self.get_id_from_external_url(self.query)
                archived_playlist = ArchivedPlaylist.objects.get(list_id=list_id)
            except (KeyError, ArchivedPlaylist.DoesNotExist):
                return False
        self.id = archived_playlist.list_id
        self.key = archived_playlist.id
        self.urls = [entry.url for entry in archived_playlist.entries.all()]
        return True

    def search_id(self) -> Optional[str]:
        """Fetches the id of this playlist from the internet and returns it."""
        raise NotImplementedError()

    def check_available(self) -> bool:
        if self.id is not None:
            return True
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

    def enqueue_placeholder(self, manually_requested) -> None:
        # Playlists have no placeholder representation.
        pass

    def remove_placeholder(self) -> None:
        pass

    def make_available(self) -> bool:
        queryset = ArchivedPlaylist.objects.filter(list_id=self.id)
        if not self.is_radio() and queryset.exists():
            archived_playlist = queryset.get()
            self.key = archived_playlist.id
            self.urls = [entry.url for entry in archived_playlist.entries.all()]
        else:
            if not self.fetch_metadata():
                return False
        return True

    def persist(self, request_ip: str, archive: bool = True) -> None:
        if self.is_radio():
            return

        assert self.id
        if self.title is None:
            logging.warning("Persisting a playlist with no title (id %s)", self.id)
            self.title = ""

        with transaction.atomic():
            queryset = ArchivedPlaylist.objects.filter(list_id=self.id)
            if queryset.count() == 0:
                initial_counter = 1 if archive else 0
                archived_playlist = ArchivedPlaylist.objects.create(
                    list_id=self.id, title=self.title, counter=initial_counter
                )
                for index, url in enumerate(self.urls):
                    PlaylistEntry.objects.create(
                        playlist=archived_playlist, index=index, url=url,
                    )
            else:
                if archive:
                    queryset.update(counter=F("counter") + 1)
                archived_playlist = queryset.get()

        if archive:
            ArchivedPlaylistQuery.objects.get_or_create(
                playlist=archived_playlist, query=self.query
            )

        if self.musiq.base.settings.basic.logging_enabled and request_ip:
            RequestLog.objects.create(playlist=archived_playlist, address=request_ip)

    def enqueue(self) -> None:
        for index, external_url in enumerate(self.urls):
            if index == self.musiq.base.settings.basic.max_playlist_items:
                break
            # request every url in the playlist as their own url
            song_provider = SongProvider.create(self.musiq, external_url=external_url)

            try:
                song_provider.request("", archive=False, manually_requested=False)
            except ProviderError:
                continue

            if settings.DEBUG:
                # the sqlite database has problems if songs are pushed very fast
                # while a new song is taken from the queue. Add a delay to mitigate.
                time.sleep(1)
