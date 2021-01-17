"""This module contains the base classes for all music providers."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from core.models import ArchivedSong
from core.util import background_thread

if TYPE_CHECKING:
    from core.musiq.musiq import Musiq


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
        self, request_ip: str, archive: bool = True, manually_requested: bool = True
    ) -> None:
        """Tries to request this resource.
        Uses the local cache if possible, otherwise tries to retrieve it online."""

        def enqueue() -> None:
            self.persist(request_ip, archive=archive)
            self.enqueue()

        enqueue_function = enqueue

        if not self.check_cached():
            if (
                self.query is not None
                and self.musiq.base.settings.basic.additional_keywords
            ):
                # add the additional keywords from the settings before checking
                self.query += " " + self.musiq.base.settings.basic.additional_keywords
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

        from core.musiq.song_provider import SongProvider

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
