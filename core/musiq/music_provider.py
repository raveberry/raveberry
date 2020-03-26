from core.models import ArchivedSong
from core.models import ArchivedQuery
from core.models import RequestLog

from django.db import transaction
from django.db.models import F


class MusicProvider:

    @staticmethod
    def createProvider(musiq, internal_url=None, external_url=None):
        from core.musiq.youtube import YoutubeProvider
        if (internal_url is not None and internal_url.startswith('file://')) \
                or (external_url is not None and external_url.startswith('https://www.youtube.com/')):
            return YoutubeProvider.create(musiq, internal_url=internal_url, external_url=external_url)

    def __init__(self, musiq, query, key):
        self.musiq = musiq
        self.query = query
        self.key = key
        self.id = None
        self.placeholder = None
        self.error = 'error'
        self.ok_response = 'ok'

        if key is None:
            self.archived = False
        else:
            self.archived = True

    def check_cached(self):
        pass

    def check_downloadable(self):
        pass

    def enqueue(self, ip, archive=True, manually_requested=True):
        from core.musiq.player import Player

        metadata = self.get_metadata()

        # Increase counter of song/playlist
        with transaction.atomic():
            queryset = ArchivedSong.objects.filter(url=metadata['external_url'])
            if queryset.count() == 0:
                initial_counter = 1 if archive else 0
                archived_song = ArchivedSong.objects.create(url=metadata['external_url'], artist=metadata['artist'], title=metadata['title'], counter=initial_counter)
            else:
                if archive:
                    queryset.update(counter=F('counter')+1)
                archived_song = queryset.get()

            if archive:
                ArchivedQuery.objects.get_or_create(song=archived_song, query=self.query)

        if archive and ip:
            RequestLog.objects.create(song=archived_song, address=ip)

        song = self.musiq.queue.enqueue(metadata, manually_requested)
        if self.placeholder:
            self.placeholder['replaced_by'] = song.id
        self.musiq.update_state()
        Player.queue_semaphore.release()

    def download(self, ip, background=True, archive=True, manually_requested=True):
        self.enqueue(ip, archive=archive, manually_requested=manually_requested)

    def get_suggestion(self):
        pass

    def get_metadata(self):
        return dict()

    def get_internal_url(self):
        pass