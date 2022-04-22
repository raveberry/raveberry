"""This module contains manages the song queue in the database."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional, Tuple

from django.db import models, transaction
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
        return self.exclude(internal_url=None)

    @transaction.atomic
    def delete_placeholders(self) -> None:
        """Deletes all songs from the queue that are not confirmed."""
        self.filter(internal_url=None).delete()

    @transaction.atomic
    def enqueue(
        self,
        metadata: "Metadata",
        manually_requested: bool,
        votes=0,
        enqueue_first=False,
    ) -> QueuedSong:
        """Creates a new song at the end of the queue and returns it."""
        last = self.last()
        index = 1 if last is None else last.index + 1
        song = self.create(
            index=index,
            votes=votes,
            manually_requested=manually_requested,
            artist=metadata["artist"],
            title=metadata["title"],
            duration=metadata["duration"],
            internal_url=metadata["internal_url"],
            external_url=metadata["external_url"],
            stream_url=metadata["stream_url"],
        )
        if enqueue_first:
            self.prioritize(song.id)
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
    def deprioritize(self, key: int) -> None:
        """Moves the song specified by :param key: to the end of the queue."""
        to_deprioritize = self.get(id=key)
        last = self.last()
        if to_deprioritize == last:
            return

        self.filter(index__gt=to_deprioritize.index).update(index=F("index") - 1)
        to_deprioritize.index = self.count()
        to_deprioritize.save()

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

        new_prev = self.filter(id=new_prev_id).first()
        try:
            to_reorder = self.get(id=element_id)
        except core.models.QueuedSong.DoesNotExist as error:
            raise ValueError("reordered song does not exist") from error
        new_next = self.filter(id=new_next_id).first()

        first = self.first()
        last = self.last()
        # check validity of request
        if new_prev is None and new_next is None:
            # to_reorder has to be the only element in the queue
            if first != to_reorder or last != to_reorder:
                raise ValueError("reordered song is not the only one")
            # nothing to do
            return
        if new_prev is None:
            # new_next has to be the first element
            if new_next != first:
                raise ValueError("given first is not head of the queue")
            assert new_next
            self.prioritize(element_id)
            return
        if new_next is None:
            # new_prev has to be the last element
            if new_prev != last:
                raise ValueError("given last is not tail of the queue")
            self.deprioritize(element_id)
            return
        # neither new_prev and new_next are None
        # new_prev and new_next have to be adjacent
        if new_next.index != new_prev.index + 1:
            raise ValueError("given pair of songs is not adjacent")

        # update indices
        moving_up = True
        if new_prev.index > to_reorder.index or new_next.index > to_reorder.index:
            moving_up = False

        to_update = self.all()
        if moving_up:
            new_index = new_next.index
            to_update = to_update.filter(index__lte=to_reorder.index - 1)
            to_update = to_update.filter(index__gte=new_next.index)
            to_update.update(index=F("index") + 1)
        else:
            new_index = new_prev.index
            to_update = to_update.filter(index__lte=new_prev.index)
            to_update = to_update.filter(index__gte=to_reorder.index + 1)
            to_update.update(index=F("index") - 1)

        to_reorder.index = new_index
        to_reorder.save()

    @transaction.atomic
    def shuffle(self) -> None:
        """Assigns a random index to every song in the queue."""
        indices = list(range(1, self.count() + 1))
        random.shuffle(indices)
        for song, index in zip(self.all(), indices):
            song.index = index
            song.save()

    @transaction.atomic
    def vote(self, key: int, amount: int, threshold: int) -> Optional["QueuedSong"]:
        """Modify the vote-count of the song specified by :param key: by :param amount: votes.
        If the song is now below the threshold, remove and return it."""
        self.filter(id=key).update(votes=F("votes") + amount)
        try:
            song = self.get(id=key)
            if song.votes <= threshold:
                song.delete()
                return song
        except core.models.QueuedSong.DoesNotExist:
            pass
        return None
