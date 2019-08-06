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
from core.musiq.song_provider import SongProvider
from core.musiq.player import Player
from core.musiq.song_queue import SongQueue
from core.musiq.downloader import SongTooLargeException
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

    def request_song(self, request, query, check_function, get_function, key_or_query):
        ip, is_routable = ipware.get_client_ip(request)
        if ip is None:
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
                location = get_function(key_or_query, downloader, ip)
            except youtube_dl.utils.DownloadError as e:
                error = e
            
            if error is not None or location is None:
                self.logger.error('accessible video could not be downloaded: ' + str(key_or_query))
                self.logger.error(error)
                self.logger.error('location: ' + str(location))
                self.placeholders.remove(placeholder);
                self.update_state()
                return

            song = self.queue.enqueue(location)
            placeholder['replaced_by'] = song.id
            self.update_state()
            Player.queue_semaphore.release()
        
        threading.Thread(target=get_song, daemon=True).start()

        return HttpResponse('Song queued')

    def request_archived_song(self, request):
        key = request.POST.get('key')
        if key is None:
            return HttpResponseBadRequest()
        query = request.POST.get('query')

        return self.request_song(request, query, self.song_provider.check_archived_song_accessible, self.song_provider.get_archived_song_location, key)

    def request_new_song(self, request):
        query = request.POST.get('query')
        if query is None or query == '':
            return HttpResponseBadRequest()

        return self.request_song(request, query, self.song_provider.check_new_song_accessible, self.song_provider.get_new_song_location, query)

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
