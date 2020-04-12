import json
import os
import time

import django
from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from tests import util

from core.models import ArchivedSong, ArchivedPlaylist, CurrentSong, QueuedSong


class MusicTest(TransactionTestCase):

    def setUp(self):
        self.client = Client()
        util.admin_login(self.client)

        # reduce number of downloaded songs for the test
        self.client.post(reverse('set_max_playlist_items'), {'value': '5'})

        self.client.post(reverse('start_player_loop'))

    def tearDown(self):
        self.client.login(username='admin', password='admin')

        # restore player state
        self.client.post(reverse('set_autoplay'), {'value': 'false'})
        self._poll_musiq_state(lambda state: not state['autoplay'])

        # ensure that the player is not waiting for a song to finish
        self.client.post(reverse('remove_all'))
        self._poll_musiq_state(lambda state: len(state['song_queue']) == 0)
        self.client.post(reverse('skip_song'))
        self._poll_musiq_state(lambda state: not state['current_song'])

        self.client.post(reverse('stop_player_loop'))

    def _setup_test_library(self):
        util.download_test_library()

        test_library = os.path.join(settings.BASE_DIR, 'test_library')
        self.client.post(reverse('scan_library'), {'library_path': test_library})
        # need to split the scan_progress as it contains no-break spaces
        self._poll_state('settings_state', lambda state: ' '.join(state['scan_progress'].split()).startswith('6 / 6 / '))
        self.client.post(reverse('create_playlists'))
        self._poll_state('settings_state', lambda state: ' '.join(state['scan_progress'].split()).startswith('6 / 6 / '))

    def _poll_state(self, state_url, break_condition, timeout=1):
        timeout *= 10
        counter = 0
        while counter < timeout:
            state = json.loads(self.client.get(reverse(state_url)).content)
            if break_condition(state):
                break
            time.sleep(0.1)
            counter += 1
        else:
            self.fail(f'enqueue timeout. state: {state}')
        return state

    def _poll_musiq_state(self, break_condition, timeout=1):
        return self._poll_state('musiq_state', break_condition, timeout=timeout)

    def _poll_current_song(self):
        state = self._poll_musiq_state(lambda state: state['current_song'], timeout=10)
        current_song = state['current_song']
        return current_song

    def _add_local_playlist(self):
        suggestion = json.loads(self.client.get(reverse('suggestions'), {'term': 'hard rock', 'playlist': 'true'}).content)[0]
        self.client.post(reverse('request_music'), {'key': suggestion['key'], 'query': '', 'playlist': 'true', 'platform': 'local'})
        state = self._poll_musiq_state(lambda state: len(state['song_queue']) == 3 and all(song['confirmed'] for song in state['song_queue']), timeout=3)
        return state
