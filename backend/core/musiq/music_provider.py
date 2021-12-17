"""This module contains the base class of all music providers."""

from __future__ import annotations

from typing import Optional

from core.settings import storage
from core.celery import app
from core.models import ArchivedSong
from core.musiq import musiq, playback


class ProviderError(Exception):
    """An error to indicate that an error occurred while providing music."""


class WrongUrlError(Exception):
    """An error to indicate that a provider was called
    with a url that belongs to a different service."""


class MusicProvider:
    """The base class for all music providers.
    Provides abstract function declarations."""

    def __init__(self, query: Optional[str], key: Optional[int]) -> None:
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

    def persist(self, session_key: str, archive: bool = True) -> None:
        """Updates the database.
        Creates an archived entry or updates it.
        Also handles logging to database."""
        raise NotImplementedError()

    def enqueue(self) -> None:
        """Updates the placeholder in the song queue with the actual data."""
        raise NotImplementedError()

    def request(
        self, session_key: str, archive: bool = True, manually_requested: bool = True
    ) -> None:
        """Tries to request this resource.
        Uses the local cache if possible, otherwise tries to retrieve it online."""

        if 0 < storage.get("max_queue_length") <= playback.queue.count():
            self.error = "Queue limit reached"
            raise ProviderError(self.error)

        enqueue_function = enqueue

        if not self.check_cached():
            if self.query is not None and storage.get("additional_keywords"):
                # add the additional keywords from the settings before checking
                self.query += " " + storage.get("additional_keywords")
            if not self.check_available():
                raise ProviderError(self.error)

            # overwrite the enqueue function and make the resource available before calling it
            enqueue_function = fetch_enqueue

        from core.musiq.song_provider import SongProvider

        if storage.get("new_music_only") and isinstance(self, SongProvider):
            try:
                archived_song = ArchivedSong.objects.get(url=self.get_external_url())
                if archived_song.counter > 0:
                    self.error = "Only new music is allowed!"
                    raise ProviderError(self.error)
            except ArchivedSong.DoesNotExist:
                pass

        self.enqueue_placeholder(manually_requested)

        enqueue_function.delay(self, session_key, archive)


@app.task
def enqueue(provider: MusicProvider, session_key: str, archive: bool) -> None:
    """Enqueue the music managed by the given provider."""
    provider.persist(session_key, archive=archive)
    provider.enqueue()


@app.task
def fetch_enqueue(provider: MusicProvider, session_key: str, archive: bool) -> None:
    """Fetch and enqueue the music managed by the given provider."""
    if not provider.make_available():
        provider.remove_placeholder()
        musiq.update_state()
        return

    enqueue(provider, session_key, archive)
