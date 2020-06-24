"""This module contains manages the song queue in the database."""

from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING

from django.db import models
from django.db import transaction
from django.db.models import F, QuerySet

import core.models

if TYPE_CHECKING:
    from core.models import QueuedSong
    from core.musiq.song_utils import Metadata


class SongQueue(models.Manager):
    """This is the manager for the QueuedSong model.
    Handles all operations on the queue."""

    @transaction.atomic
    def confirmed(self) -> QuerySet[QueuedSong]:
        """Returns a QuerySet containing all confirmed songs.
        Confirmed songs are not in the process of being made available."""
        return self.exclude(internal_url="")

    @transaction.atomic
    def delete_placeholders(self) -> None:
        """Deletes all songs from the queue that are not confirmed."""
        self.filter(internal_url="").delete()

    @transaction.atomic
    def enqueue(
        self, metadata: "Metadata", manually_requested: bool, votes=0
    ) -> QueuedSong:
        """Creates a new song at the end of the queue and returns it."""
        last = self.last()
        index = 1 if last is None else last.index + 1
        song = self.create(
            index=index,
            votes=votes,
            manually_requested=manually_requested,
            internal_url=metadata["internal_url"],
            external_url=metadata["external_url"],
            artist=metadata["artist"],
            title=metadata["title"],
            duration=metadata["duration"],
        )
        return song

    @transaction.atomic
    def dequeue(self) -> Tuple[int, Optional["QueuedSong"]]:
        """Removes the first completed song from the queue and returns its id and the object."""
        song = self.confirmed().first()
        if song is None:
            return -1, None
        song_id = song.id
        song.delete()
        self.filter(index__gt=song.index).update(index=F("index") - 1)
        return song_id, song

    @transaction.atomic
    def prioritize(self, key: int) -> None:
        """Moves the song specified by :param key: to the front of the queue."""
        to_prioritize = self.get(id=key)
        first = self.first()
        if to_prioritize == first:
            return

        self.filter(index__lt=to_prioritize.index).update(index=F("index") + 1)
        to_prioritize.index = 1
        to_prioritize.save()

    @transaction.atomic
    def remove(self, key: int) -> "QueuedSong":
        """Removes the song specified by :param key: from the queue and returns it."""
        to_remove = self.get(id=key)
        to_remove.delete()
        self.filter(index__gt=to_remove.index).update(index=F("index") - 1)
        return to_remove

    @transaction.atomic
    def reorder(
        self, new_prev_id: Optional[int], element_id: int, new_next_id: Optional[int]
    ) -> None:
        """Moves the song specified by :param element_id:
        between the two songs :param new_prev_id: and :param new_next_id:."""

        try:
            new_prev = self.get(id=new_prev_id)
        except core.models.QueuedSong.DoesNotExist:
            new_prev = None
        try:
            to_reorder = self.get(id=element_id)
        except core.models.QueuedSong.DoesNotExist:
            raise ValueError("reordered song does not exist")
        try:
            new_next = self.get(id=new_next_id)
        except core.models.QueuedSong.DoesNotExist:
            new_next = None

        first = self.first()
        last = self.last()
        # check validity of request
        if new_prev is None and new_next is None:
            # to_reorder has to be the only element in the queue
            if first != to_reorder or last != to_reorder:
                raise ValueError("reordered song is not the only one")
        if new_prev is None and new_next is not None:
            # new_next has to be the first element
            if new_next != first:
                raise ValueError("given first is not head of the queue")
        if new_prev is not None and new_next is None:
            # new_prev has to be the last element
            if new_prev != last:
                raise ValueError("given last is not tail of the queue")
        if new_prev is not None and new_next is not None:
            # new_prev and new_next have to be adjacent
            if new_next.index != new_prev.index + 1:
                raise ValueError("given pair of songs is not adjacent")

        try:
            old_prev = self.get(index=to_reorder.index - 1)
        except core.models.QueuedSong.DoesNotExist:
            old_prev = None
        try:
            old_next = self.get(index=to_reorder.index + 1)
        except core.models.QueuedSong.DoesNotExist:
            old_next = None

        # update indices
        moving_up = True
        if new_prev is not None:
            if new_prev.index > to_reorder.index:
                moving_up = False
        elif new_next is not None:
            if new_next.index > to_reorder.index:
                moving_up = False

        to_update = self.all()
        if moving_up:
            if old_prev is not None:
                to_update = to_update.filter(index__lte=old_prev.index)
            new_index = 1
            if new_next is not None:
                new_index = new_next.index
                to_update = to_update.filter(index__gte=new_next.index)
            to_update.update(index=F("index") + 1)
        else:
            new_index = 1
            if new_prev is not None:
                new_index = new_prev.index
                to_update = to_update.filter(index__lte=new_prev.index)
            if old_next is not None:
                to_update = to_update.filter(index__gte=old_next.index)
            to_update.update(index=F("index") - 1)

        to_reorder.index = new_index
        to_reorder.save()

    @transaction.atomic
    def vote_up(self, key: int) -> None:
        """Increase the vote-count of the song specified by :param key:."""
        self.filter(id=key).update(votes=F("votes") + 1)

    @transaction.atomic
    def vote_down(self, key: int, threshold: int) -> Optional["QueuedSong"]:
        """Decrease the vote-count of the song specified by :param key:
        If the song is now below the threshold, remove and return it."""
        self.filter(id=key).update(votes=F("votes") - 1)
        try:
            song = self.get(id=key)
            if song.votes <= threshold:
                song.delete()
                return song
        except core.models.QueuedSong.DoesNotExist:
            pass
        return None
