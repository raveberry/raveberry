from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseServerError
from django.core import serializers
from django.forms.models import model_to_dict
from django.views.decorators.csrf import csrf_exempt

from core.models import QueuedSong
from core.models import CurrentSong
from core.models import ArchivedSong
from core.musiq.localdrive import LocalSongProvider
from core.musiq.music_provider import SongProvider, PlaylistProvider
from core.musiq.suggestions import Suggestions
from core.musiq.player import Player
from core.musiq.song_queue import SongQueue
from core.musiq.youtube import YoutubeSongProvider, NoPlaylistException, YoutubePlaylistProvider
from core.musiq.spotify import SpotifySongProvider, SpotifyPlaylistProvider
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

        self.suggestions = Suggestions(self)

        self.queue = QueuedSong.objects
        self.placeholders = []

        self.player = Player(self)
        self.player.start()

    def _request_music(self, ip, query, key, playlist, platform, archive=True, manually_requested=True):
        providers = []

        if playlist:
            if key is not None:
                # an archived song was requested. The key determines the SongProvider (Youtube or Spotify)
                provider = PlaylistProvider.create(self, query, key)
                if provider is None:
                    return HttpResponseBadRequest('No provider found for requested playlist')
                providers.append(provider)
            else:
                # try to use spotify if the user did not specifically request youtube
                if platform is None or platform == 'spotify':
                    if self.base.settings.spotify_enabled:
                        providers.append(SpotifyPlaylistProvider(self, query, key))
                # use Youtube as a fallback
                providers.append(YoutubePlaylistProvider(self, query, key))
        else:
            if key is not None:
                # an archived song was requested. The key determines the SongProvider (Youtube or Spotify)
                provider = SongProvider.create(self, query, key)
                if provider is None:
                    return HttpResponseBadRequest('No provider found for requested song')
                providers.append(provider)
            else:
                if platform == 'local':
                    # if a local provider was requested, use only this one as it can only come from the database -> it will probably exist
                    providers.append(LocalSongProvider(self, query, key))
                else:
                    # try to use spotify if the user did not specifically request youtube
                    if platform is None or platform == 'spotify':
                        if self.base.settings.spotify_enabled:
                            providers.append(SpotifySongProvider(self, query, key))
                    # use Youtube as a fallback
                    providers.append(YoutubeSongProvider(self, query, key))

        fallback = False
        used_provider = None
        for i, provider in enumerate(providers):
            if not provider.check_cached():
                if not provider.check_downloadable():
                    # this provider cannot provide this song, use the next provider
                    # if this was the last provider, show its error
                    if i == len(providers) - 1:
                        return HttpResponseBadRequest(provider.error)
                    fallback = True
                    continue
                if not provider.download(ip, archive=archive, manually_requested=manually_requested):
                    return HttpResponseBadRequest(provider.error)
            else:
                provider.enqueue(ip, archive=archive, manually_requested=manually_requested)
            # the current provider could provide the song, don't try the other ones
            used_provider = provider
            break
        message = used_provider.ok_message
        if fallback:
            message = message + ' (used fallback)'
        return HttpResponse(message)

    def request_music(self, request):
        key = request.POST.get('key')
        playlist = request.POST.get('playlist') == 'true'
        query = request.POST.get('query')
        platform = request.POST.get('platform')

        # only get ip on user requests
        if self.base.settings.logging_enabled:
            ip, is_routable = ipware.get_client_ip(request)
            if ip is None:
                ip = ''
        else:
            ip = ''

        return self._request_music(ip, query, key, playlist, platform)

    def request_radio(self, request):
        # only get ip on user requests
        if self.base.settings.logging_enabled:
            ip, is_routable = ipware.get_client_ip(request)
            if ip is None:
                ip = ''
        else:
            ip = ''

        try:
            current_song = CurrentSong.objects.get()
        except CurrentSong.DoesNotExist:
            return HttpResponseBadRequest('Need a song to play the radio')
        provider = SongProvider.create(self, external_url=current_song.external_url)
        return provider.request_radio(ip)

    @csrf_exempt
    def post_song(self, request):
        return self.request_music(request)

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
            song_dict['duration_formatted'] = song_utils.format_seconds(song_dict['duration'])
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

        if state_dict['alarm']:
            state_dict['current_song'] = {
                'queue_key': -1,
                'manually_requested': False,
                'votes': None,
                'internal_url': '',
                'external_url': '',
                'artist': 'Raveberry',
                'title': 'ALARM!',
                'duration': 10,
                'created': ''
            }
        else:
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
