from django.db import transaction
from django.db.models import Q
from django.db.models import F
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse

from core.musiq.youtube import Downloader
from core.musiq.youtube import NoPlaylistException
import core.musiq.youtube as youtube
from core.models import ArchivedSong
from core.models import ArchivedPlaylist
from core.models import ArchivedQuery
from core.models import ArchivedPlaylistQuery
from core.models import PlaylistEntry
from core.models import RequestLog
import core.musiq.song_utils as song_utils

import json
import random

class OfflineDownloader():
    def __init__(self, location):
        self.location = location
    def fetch(self):
        return self.location

class SongProvider:

    def __init__(self, musiq):
        self.musiq = musiq

    def check_archived_song_accessible(self, key):
        archived_song = ArchivedSong.objects.get(id=key)
        location = song_utils.path_from_url(archived_song.url)
        downloader = None
        if not location:
            downloader = Downloader(self.musiq, archived_song.url)
            downloader.check()
        # the downloader raised no error, the song is accessible
        return downloader

    def get_archived_song_location(self, key, downloader, ip, archive=True):
        archived_song = ArchivedSong.objects.get(id=key)
        location = song_utils.path_from_url(archived_song.url)
        if location is None:
            location = downloader.fetch()
        if archive:
            ArchivedSong.objects.filter(id=key).update(counter=F('counter')+1)
        if archive and self.musiq.base.settings.logging_enabled:
            RequestLog.objects.create(song=archived_song, address=ip)
        return location

    def check_new_song_accessible(self, search_text):
        # collapse whitespaces
        search_text = ' '.join(search_text.split())

        # if the search text is a url that is already in the database and the song is cached offline, we don't need an online downloader
        downloader = None
        queryset = ArchivedSong.objects.filter(url=search_text)
        if queryset.count() == 1:
            song = queryset.get()
            location = song_utils.path_from_url(song.url)
            if location is not None:
                downloader = OfflineDownloader(location)

        # if the song was not found offline, we use the online downloader
        if downloader is None:
            downloader = Downloader(self.musiq, search_text)
            downloader.check()
            # the downloader raised no error, the song is accessible
        return downloader

    def get_new_song_location(self, search_text, downloader, ip, archive=True):
        location = downloader.fetch()

        metadata = song_utils.gather_metadata(location)

        with transaction.atomic():
            queryset = ArchivedSong.objects.filter(url=metadata['url'])
            if queryset.count() == 0:
                initial_counter = 1 if archive else 0
                archived_song = ArchivedSong.objects.create(url=metadata['url'], artist=metadata['artist'], title=metadata['title'], counter=initial_counter)
            else:
                if archive:
                    queryset.update(counter=F('counter')+1)
                archived_song = queryset.get()

            if archive:
                ArchivedQuery.objects.get_or_create(song=archived_song, query=search_text)

        if archive and self.musiq.base.settings.logging_enabled:
            RequestLog.objects.create(song=archived_song, address=ip)
        return location

    def get_new_playlist(self, query, ip):
        try:
            downloader = Downloader(self.musiq, query)
            playlist_info = downloader.get_playlist_info()
        except NoPlaylistException:
            # no valid playlist url was provided. use the query as a search
            list_id = youtube.search_playlist(query)
            downloader = Downloader(self.musiq, list_id)
            playlist_info = downloader.get_playlist_info()

        if playlist_info['id'].startswith('RD'):
            # the radio for a given song can be different every time it is accessed
            # thus, we create a new database entry every time a radio is requested
            radio = True
        else:
            radio = False

        with transaction.atomic():
            queryset = ArchivedPlaylist.objects.filter(list_id=playlist_info['id'])
            if radio or queryset.count() == 0:
                archived_playlist = ArchivedPlaylist.objects.create(list_id=playlist_info['id'], title=playlist_info['title'], counter=1)
                for index, url in enumerate(playlist_info['urls']):
                    PlaylistEntry.objects.create(
                        playlist=archived_playlist,
                        index=index,
                        url=url,
                    )
            else:
                queryset.update(counter=F('counter')+1)
                archived_playlist = queryset.get()

            ArchivedPlaylistQuery.objects.get_or_create(playlist=archived_playlist, query=query)

        if self.musiq.base.settings.logging_enabled:
            RequestLog.objects.create(playlist=archived_playlist, address=ip)

        return archived_playlist

    def get_archived_playlist(self, key, ip):
        archived_playlist = ArchivedPlaylist.objects.get(id=key)
        ArchivedPlaylist.objects.filter(id=key).update(counter=F('counter')+1)
        if self.musiq.base.settings.logging_enabled:
            RequestLog.objects.create(playlist=archived_playlist, address=ip)
        return archived_playlist

    def random_suggestion(self, request):
        suggest_playlist = request.GET['playlist'] == 'true'
        if suggest_playlist:
            # exclude radios from suggestions
            remaining_playlists = ArchivedPlaylist.objects.all().exclude(list_id__startswith='RD').exclude(list_id__contains='&list=RD')
            if remaining_playlists.count() == 0:
                return HttpResponseBadRequest('No playlists to suggest from')
            index = random.randint(0, remaining_playlists.count() - 1)
            playlist = remaining_playlists.all()[index]
            return JsonResponse({
                'suggestion': playlist.title,
                'key': playlist.id,
            })
        else:
            if ArchivedSong.objects.count() == 0:
                return HttpResponseBadRequest('No songs to suggest from')
            index = random.randint(0,ArchivedSong.objects.count() - 1)
            song = ArchivedSong.objects.all()[index]
            return JsonResponse({
                'suggestion': song.displayname(),
                'key': song.id,
            })

    def get_suggestions(self, request):
        terms = request.GET['term'].split()
        suggest_playlist = request.GET['playlist'] == 'true'

        results = []
        if suggest_playlist:
            remaining_playlists = ArchivedPlaylist.objects.prefetch_related('queries')
            # exclude radios from suggestions
            remaining_playlists = remaining_playlists.exclude(list_id__startswith='RD').exclude(list_id__contains='&list=RD')

            for term in terms:
                remaining_playlists = remaining_playlists.filter(Q(title__icontains=term) | Q(queries__query__icontains=term))

            remaining_playlists = remaining_playlists \
                .values('id', 'title', 'counter') \
                .distinct() \
                .order_by('-counter') \
                [:20]

            for playlist in remaining_playlists:
                cached = False
                result_dict = {
                    'key': playlist['id'],
                    'value': playlist['title'],
                    'counter': playlist['counter'],
                    'type': 'cached' if cached else 'online',
                }
                results.append(result_dict)
        else:
            remaining_songs = ArchivedSong.objects.prefetch_related('queries')

            for term in terms:
                remaining_songs = remaining_songs.filter(Q(title__icontains=term) | Q(artist__icontains=term) | Q(queries__query__icontains=term))

            remaining_songs = remaining_songs \
                .values('id', 'title', 'url', 'artist', 'counter') \
                .distinct() \
                .order_by('-counter') \
                [:20]

            for song in remaining_songs:
                if song_utils.path_from_url(song['url']) is not None:
                    cached = True
                else:
                    cached = False
                # don't suggest online songs when we don't have internet
                if not self.musiq.base.settings.has_internet:
                    if not cached:
                        continue
                result_dict = {
                    'key': song['id'],
                    'value': song_utils.displayname(song['artist'], song['title']),
                    'counter': song['counter'],
                    'type': 'cached' if cached else 'online',
                }
                results.append(result_dict)

        return HttpResponse(json.dumps(results))

""" query for the suggestions
SELECT DISTINCT id, title, artist, counter
FROM core_archivedsong s LEFT JOIN core_archivedquery q ON q.song
WHERE forall term in terms: term in q.query or term in s.artist or term in s.title
ORDER BY -counter
"""
