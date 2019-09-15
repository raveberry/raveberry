from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseServerError
from django.core import serializers
from django.forms.models import model_to_dict

from core.models import QueuedSong
from core.models import CurrentSong
from core.models import ArchivedSong
from core.musiq.song_provider import SongProvider
from core.musiq.player import Player
from core.musiq.song_queue import SongQueue
from core.musiq.youtube import SongTooLargeException
from core.musiq.youtube import NoPlaylistException
import core.musiq.song_utils as song_utils
import core.state_handler as state_handler

import youtube_dl
import re
import threading

import time
import logging
import ipware

class Musiq:

    def __init__(self, base):
        self.base = base

        self.logger = logging.getLogger('raveberry')

        self.song_provider = SongProvider(self)

        self.queue = QueuedSong.objects
        self.placeholders = []

        self.player = Player(self)
        self.player.start()

    def request_song(self, request, query, check_function, get_function, key_or_query, archive=True, background_download=True):
        # only get ip on user requests
        if request is not None:
            ip, is_routable = ipware.get_client_ip(request)
            if ip is None:
                ip = ''
        else:
            ip = ''

        try:
            downloader = check_function(key_or_query)
        except (youtube_dl.utils.DownloadError, SongTooLargeException) as e:
            self.logger.info('video not accessible: ' + str(key_or_query))
            self.logger.info(e)
            return HttpResponseBadRequest(e)

        placeholder = {'query': query, 'replaced_by': None}
        self.placeholders.append(placeholder)
        self.update_state()

        def get_song():
            error = None
            location = None
            try:
                location = get_function(key_or_query, downloader, ip, archive=archive)
            except youtube_dl.utils.DownloadError as e:
                error = e
            
            if error is not None or location is None:
                self.logger.error('accessible video could not be downloaded: ' + str(key_or_query))
                self.logger.error(error)
                self.logger.error('location: ' + str(location))
                self.placeholders.remove(placeholder);
                self.update_state()
                return

            # if there is an actual request object, it was initiated by a user
            manually_requested = request is not None
            song = self.queue.enqueue(location, manually_requested)
            placeholder['replaced_by'] = song.id
            self.update_state()
            Player.queue_semaphore.release()
        
        thread = threading.Thread(target=get_song, daemon=True)
        thread.start()
        if not background_download:
            thread.join()

        return HttpResponse('Song queued')

    def request_playlist(self, request, get_function, key_or_query):
        ip, is_routable = ipware.get_client_ip(request)
        if ip is None:
            ip = ''

        try:
            playlist = get_function(key_or_query, ip)
        except (youtube_dl.utils.DownloadError, NoPlaylistException) as e:
            self.logger.info('playlist not accessible: ' + str(key_or_query))
            self.logger.info(e)
            return HttpResponseBadRequest(e)

        def get_playlist():
            for index, entry in enumerate(playlist.entries.all()):
                if index == self.base.settings.max_playlist_items:
                    break
                # request every url in the playlist as their own url
                response = self.request_song(None, entry.url, self.song_provider.check_new_song_accessible, self.song_provider.get_new_song_location, entry.url, archive=False, background_download=False)
                if settings.DEBUG:
                    # the sqlite database has problems if songs are pushed very fast while a new song is taken from the queue. Add a delay to mitigate.
                    time.sleep(1)
                # after the download finished successfully, the song definitely exists in the database. Now we can update the reference in the playlist entry.
                # after an error the song was not pushed and there exists no database entry. Then, we skip the update and leave the field empty.
                if type(response) == HttpResponse:
                    queryset = ArchivedSong.objects.filter(url=entry.url)
                    song = queryset.get()
                    entry.song = song
                    entry.save()
        threading.Thread(target=get_playlist, daemon=True).start()

        return HttpResponse('Queuing playlist')

    def request_archived_music(self, request):
        key = request.POST.get('key')
        playlist = request.POST.get('playlist') == 'true'
        if key is None:
            return HttpResponseBadRequest()
        query = request.POST.get('query')

        if playlist:
            return self.request_playlist(request, self.song_provider.get_archived_playlist, key)
        else:
            return self.request_song(request, query, self.song_provider.check_archived_song_accessible, self.song_provider.get_archived_song_location, key)

    def request_new_music(self, request):
        query = request.POST.get('query')
        playlist = request.POST.get('playlist') == 'true'
        if query is None or query == '':
            return HttpResponseBadRequest()

        if playlist:
            return self.request_playlist(request, self.song_provider.get_new_playlist, query)
        else:
            return self.request_song(request, query, self.song_provider.check_new_song_accessible, self.song_provider.get_new_song_location, query)

    def request_radio(self, request):
        try:
            current_song = CurrentSong.objects.get()
        except CurrentSong.DoesNotExist:
            return HttpResponseBadRequest('Need a song to play the radio')
        song_id = song_utils.id_from_url(current_song.url)
        radio_id = 'RD' + song_id
        response = self.request_playlist(request, self.song_provider.get_new_playlist, radio_id)
        if type(response) == HttpResponse:
            return HttpResponse('Queuing radio')
        else:
            return response

    def index(self, request):
        context = self.base.context(request)
        return render(request, 'musiq.html', context)

    def state_dict(self):
        state_dict = self.base.state_dict()
        try:
            current_song = CurrentSong.objects.get()
            current_song = model_to_dict(current_song)
        except CurrentSong.DoesNotExist:
            current_song = None
        song_queue = []
        all_songs = self.queue.all()
        if self.base.settings.voting_system:
            all_songs = all_songs.order_by('-votes', 'index')
        for song in all_songs:
            song_dict = model_to_dict(song)
            song_dict['confirmed'] = True
            # find the query of the placeholder that this song replaces (if any)
            for i, placeholder in enumerate(self.placeholders[:]):
                if placeholder['replaced_by'] == song.id:
                    song_dict['replaces'] = placeholder['query']
                    self.placeholders.remove(placeholder)
                    break
            else:
                song_dict['replaces'] = None
            song_queue.append(song_dict)
        song_queue += [{'title': placeholder['query'], 'confirmed': False} for placeholder in self.placeholders]

        state_dict['current_song'] =  current_song
        state_dict['paused'] =  self.player.paused()
        state_dict['progress'] =  self.player.progress()
        state_dict['shuffle'] =  self.player.shuffle
        state_dict['repeat'] =  self.player.repeat
        state_dict['autoplay'] =  self.player.autoplay
        state_dict['volume'] =  self.player.volume
        state_dict['song_queue'] =  song_queue
        return state_dict

    def get_state(self, request):
        state = self.state_dict()
        return JsonResponse(state)

    def update_state(self):
        state_handler.update_state(self.state_dict())
