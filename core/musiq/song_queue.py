from django.conf import settings
from django.db import models
from django.db import transaction
from django.db.models import F

import core.musiq.song_utils as song_utils
import core.models

class SongQueue(models.Manager):

    @transaction.atomic
    def enqueue(self, metadata, manually_requested):
        last = self.last()
        index = 1 if last is None else last.index + 1
        song = self.create(
                index=index,
                manually_requested=manually_requested,
                internal_url=metadata['internal_url'],
                external_url=metadata['external_url'],
                artist=metadata['artist'],
                title=metadata['title'],
                duration=metadata['duration'])
        return song

    @transaction.atomic
    def dequeue(self):
        first = self.first()
        first_id = first.id
        if first is not None:
            first.delete()
        self.update(index=F('index')-1)
        return first_id, first

    @transaction.atomic
    def prioritize(self, key):
        to_prioritize = self.get(id=key)
        first = self.first()
        if to_prioritize == first:
            return

        self.filter(index__lt=to_prioritize.index).update(index=F('index')+1)
        to_prioritize.index = 1
        to_prioritize.save()


    @transaction.atomic
    def remove(self, key):
        to_remove = self.get(id=key)
        to_remove.delete()
        if next is not None:
            self.filter(index__gt=to_remove.index).update(index=F('index')-1)
        return to_remove

    @transaction.atomic
    def reorder(self, new_prev_id, element_id, new_next_id):

        try:
            new_prev = self.get(id=new_prev_id)
        except core.models.QueuedSong.DoesNotExist:
            new_prev = None
        try:
            to_reorder = self.get(id=element_id)
        except core.models.QueuedSong.DoesNotExist:
            raise ValueError('reordered song does not exist')
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
                raise ValueError('reordered song is not the only one')
        if new_prev is None and new_next is not None:
            # new_next has to be the first element
            if new_next != first:
                raise ValueError('given first is not head of the queue')
        if new_prev is not None and new_next is None:
            # new_prev has to be the last element
            if new_prev != last:
                raise ValueError('given last is not tail of the queue')
        if new_prev is not None and new_next is not None:
            # new_prev and new_next have to be adjacent
            if new_next.index != new_prev.index + 1:
                raise ValueError('given pair of songs is not adjacent')

        try:
            old_prev = self.get(index=to_reorder.index-1)
        except core.models.QueuedSong.DoesNotExist:
            old_prev = None
        try:
            old_next = self.get(index=to_reorder.index+1)
        except core.models.QueuedSong.DoesNotExist:
            old_next = None

        # update indices
        up = True
        if new_prev is not None:
            if new_prev.index > to_reorder.index:
                up = False
        elif new_next is not None:
            if new_next.index > to_reorder.index:
                up = False

        to_update = self.all()
        if up:
            if old_prev is not None:
                to_update = to_update.filter(index__lte=old_prev.index)
            new_index = 1
            if new_next is not None:
                new_index = new_next.index
                to_update = to_update.filter(index__gte=new_next.index)
            to_update.update(index=F('index')+1)
        else:
            new_index = 1
            if new_prev is not None:
                new_index = new_prev.index
                to_update = to_update.filter(index__lte=new_prev.index)
            if old_next is not None:
                to_update = to_update.filter(index__gte=old_next.index)
            to_update.update(index=F('index')-1)

        to_reorder.index = new_index
        to_reorder.save()

    @transaction.atomic
    def vote_up(self, key):
        self.filter(id=key).update(votes=F('votes')+1)

    @transaction.atomic
    def vote_down(self, key, threshold):
        self.filter(id=key).update(votes=F('votes')-1)
        try:
            song = self.get(id=key)
            if song.votes <= threshold:
                song.delete()
                return song
        except core.models.QueuedSong.DoesNotExist:
            pass
        return None
