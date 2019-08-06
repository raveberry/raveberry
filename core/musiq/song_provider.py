from django.db import transaction
from django.db.models import Q
from django.db.models import F
from django.http import HttpResponse
from django.http import JsonResponse

from core.musiq.downloader import Downloader
from core.models import ArchivedSong
from core.models import ArchivedQuery
from core.models import RequestLog
import core.musiq.song_utils as song_utils

import json
import random

class SongProvider:

    def __init__(self, musiq):
        self.musiq = musiq

    def check_archived_song_accessible(self, key):
        archived_song = ArchivedSong.objects.get(id=key)
        location = song_utils.path_from_url(archived_song.url)
        downloader = None
        if not location:
            downloader = Downloader(self.musiq)
            downloader.check(archived_song.url)
        # the downloader raised no error, the song is accessible
        return downloader

    def get_archived_song_location(self, key, downloader, ip):
        archived_song = ArchivedSong.objects.get(id=key)
        location = song_utils.path_from_url(archived_song.url)
        if location is None:
            location = downloader.fetch(archived_song.url)
        ArchivedSong.objects.filter(id=key).update(counter=F('counter')+1)
        if self.musiq.base.settings.logging_enabled:
            RequestLog.objects.create(song=archived_song, address=ip)
        return location

    def check_new_song_accessible(self, search_text):
        # collapse whitespaces
        search_text = ' '.join(search_text.split())
        downloader = Downloader(self.musiq)
        downloader.check(search_text)
        # the downloader raised no error, the song is accessible
        return downloader

    def get_new_song_location(self, search_text, downloader, ip):
        location = downloader.fetch(search_text)
        archived_song = self._archive(location, search_text)
        if self.musiq.base.settings.logging_enabled:
            RequestLog.objects.create(song=archived_song, address=ip)
        return location
    
    def _archive(self, location, query):
        metadata = song_utils.gather_metadata(location)

        with transaction.atomic():
            queryset = ArchivedSong.objects.filter(url=metadata['url'])
            if queryset.count() == 0:
                archived_song = ArchivedSong.objects.create(url=metadata['url'], artist=metadata['artist'], title=metadata['title'], counter=1)
            else:
                queryset.update(counter=F('counter')+1)
                archived_song = queryset.get()

            ArchivedQuery.objects.get_or_create(song=archived_song, query=query)
        return archived_song

    def random_suggestion(self, request):
        index = random.randint(0,ArchivedSong.objects.count() - 1)
        song = ArchivedSong.objects.all()[index]
        return JsonResponse({
            'suggestion': song.displayname(),
            'key': song.id,
        })

    def get_suggestions(self, request):
        terms = request.GET['term'].split()

        remaining_songs = ArchivedQuery.objects.select_related('song') \
            .values('song__id', 'song__title', 'song__url', 'song__artist', 'song__counter', 'query')

        for term in terms:
            remaining_songs = remaining_songs.filter(Q(song__title__icontains=term) | Q(song__artist__icontains=term) | Q(query__icontains=term))

        remaining_songs = remaining_songs \
            .values('song__id', 'song__title', 'song__url', 'song__artist', 'song__counter') \
            .distinct() \
            .order_by('-song__counter') \
            [:20]

        results = []
        for song in remaining_songs:
            if song_utils.path_from_url(song['song__url']) is not None:
                cached = True
            else:
                cached = False
            # don't suggest online songs when we don't have internet
            if not self.musiq.base.settings.has_internet:
                if not cached:
                    continue
            result_dict = {
                'key': song['song__id'],
                'value': song_utils.displayname(song['song__artist'], song['song__title']),
                'counter': song['song__counter'],
                'type': 'cached' if cached else 'online',
            }
            results.append(result_dict)

        return HttpResponse(json.dumps(results))


""" query for the suggestions
SELECT DISTINCT id, title, artist, counter
FROM core_archivedsong s JOIN core_archivedquery q ON q.song
WHERE forall term in terms: term in q.query or term in s.artist or term in s.title
ORDER BY -counter
"""
