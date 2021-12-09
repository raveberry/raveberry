"""This module contains the base class of all song providers."""

import logging
from typing import Optional, Type, TYPE_CHECKING

from django.db import transaction
from django.db.models.expressions import F
from django.http.response import HttpResponse

import core.settings.storage as storage
from core.models import ArchivedSong, QueuedSong, ArchivedQuery, RequestLog
from core.musiq import song_utils as song_utils, playback
from core.musiq import musiq
from core.musiq.music_provider import MusicProvider, WrongUrlError

if TYPE_CHECKING:
    from core.musiq.song_utils import Metadata


class SongProvider(MusicProvider):
    """The base class for all single song providers."""

    @staticmethod
    def get_id_from_external_url(url: str) -> str:
        """Constructs and returns the external id based on the given url."""
        raise NotImplementedError()

    @staticmethod
    def create(
        query: Optional[str] = None,
        key: Optional[int] = None,
        external_url: Optional[str] = None,
    ) -> "SongProvider":
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
        elif storage.get("youtube_enabled") and url_type == "youtube":
            from core.musiq.youtube import YoutubeSongProvider

            provider_class = YoutubeSongProvider
        elif storage.get("spotify_enabled") and url_type == "spotify":
            from core.musiq.spotify import SpotifySongProvider

            provider_class = SpotifySongProvider
        elif storage.get("soundcloud_enabled") and url_type == "soundcloud":
            from core.musiq.soundcloud import SoundcloudSongProvider

            provider_class = SoundcloudSongProvider
        elif storage.get("jamendo_enabled") and url_type == "jamendo":
            from core.musiq.jamendo import JamendoSongProvider

            provider_class = JamendoSongProvider
        if not provider_class:
            raise NotImplementedError(f"No provider for given song: {external_url}")
        if not query and external_url:
            query = external_url
        provider = provider_class(query, key)
        return provider

    def __init__(self, query: Optional[str], key: Optional[int]) -> None:
        super().__init__(query, key)
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
            if url_type == "local":
                from core.musiq.localdrive import LocalSongProvider

                return LocalSongProvider.get_id_from_external_url(self.query)
            if storage.get("youtube_enabled") and url_type == "youtube":
                from core.musiq.youtube import YoutubeSongProvider

                return YoutubeSongProvider.get_id_from_external_url(self.query)
            if storage.get("spotify_enabled") and url_type == "spotify":
                from core.musiq.spotify import SpotifySongProvider

                return SpotifySongProvider.get_id_from_external_url(self.query)
            if storage.get("soundcloud_enabled") and url_type == "soundcloud":
                from core.musiq.soundcloud import SoundcloudSongProvider

                return SoundcloudSongProvider.get_id_from_external_url(self.query)
            if storage.get("jamendo_enabled") and url_type == "jamendo":
                from core.musiq.jamendo import JamendoSongProvider

                return JamendoSongProvider.get_id_from_external_url(self.query)
            try:
                archived_song = ArchivedSong.objects.get(url=self.query)
                return self.__class__.get_id_from_external_url(archived_song.url)
            except ArchivedSong.DoesNotExist:
                return None
        logging.error("Can not extract id because neither key nor query are known")
        return None

    def enqueue_placeholder(self, manually_requested) -> None:
        metadata: Metadata = {
            "artist": "",
            "title": self.query or self.get_external_url(),
            "duration": -1,
            "internal_url": None,
            "external_url": self.get_external_url(),
            "stream_url": None,
            "cached": False,
        }
        initial_votes = 1 if manually_requested else 0
        self.queued_song = playback.queue.enqueue(
            metadata, manually_requested, votes=initial_votes
        )

    def remove_placeholder(self) -> None:
        assert self.queued_song
        self.queued_song.delete()

    def check_cached(self) -> bool:
        raise NotImplementedError()

    def check_not_too_large(self, size: Optional[float]) -> bool:
        max_size = storage.get("max_download_size") * 1024 * 1024
        if (
            max_size != 0
            and not self.check_cached()
            and (size is not None and size > max_size)
        ):
            self.error = "Song too long"
            return False
        return True

    def check_available(self) -> bool:
        raise NotImplementedError()

    def make_available(self) -> bool:
        return True

    def persist(self, session_key: str, archive: bool = True) -> None:
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
                    duration=metadata["duration"],
                    counter=initial_counter,
                    cached=metadata["cached"],
                )
            else:
                if archive:
                    queryset.update(counter=F("counter") + 1)
                archived_song = queryset.get()

            if archive:
                ArchivedQuery.objects.get_or_create(
                    song=archived_song, query=self.query
                )

        if storage.get("logging_enabled") and session_key:
            RequestLog.objects.create(song=archived_song, session_key=session_key)

    def enqueue(self) -> None:
        assert self.queued_song
        if not playback.queue.filter(id=self.queued_song.id).exists():
            # this song was already deleted, do not enqueue
            return

        metadata = self.get_metadata()

        self.queued_song.artist = metadata["artist"]
        self.queued_song.title = metadata["title"]
        self.queued_song.duration = metadata["duration"]
        self.queued_song.internal_url = metadata["internal_url"]
        self.queued_song.external_url = metadata["external_url"]
        self.queued_song.stream_url = metadata["stream_url"]
        # make sure not to overwrite the index as it may have changed in the meantime
        self.queued_song.save(
            update_fields=[
                "artist",
                "title",
                "duration",
                "internal_url",
                "external_url",
                "stream_url",
            ]
        )

        musiq.update_state()
        playback.queue_changed.set()

    def get_suggestion(self) -> str:
        """Returns the external url of a suggested song based on this one."""
        raise NotImplementedError()

    def get_metadata(self) -> "Metadata":
        """Returns a dictionary of this song's metadata."""
        raise NotImplementedError()

    def request_radio(self, session_key) -> HttpResponse:
        """Enqueues a playlist of songs based on this one."""
        raise NotImplementedError()
