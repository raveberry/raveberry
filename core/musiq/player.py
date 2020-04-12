from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseBadRequest
from django.utils import timezone
from django.conf import settings

from core.models import Setting
import core.models as models
import core.musiq.song_utils as song_utils

from threading import Semaphore
from threading import Lock
from threading import Event
from datetime import datetime
from functools import wraps
from contextlib import contextmanager
from requests.exceptions import ConnectionError
import os
import time
import random
import subprocess
import mopidy.core
import mopidy.backend
from mopidyapi import MopidyAPI
from mopidyapi.exceptions import MopidyError

from core.musiq.music_provider import SongProvider
from core.util import background_thread


class Player:
    queue_semaphore = None

    def __init__(self, musiq):
        self.SEEK_DISTANCE = 10 * 1000
        self.shuffle = Setting.objects.get_or_create(key='shuffle', defaults={'value': 'False'})[0].value == 'True'
        self.repeat = Setting.objects.get_or_create(key='repeat', defaults={'value': 'False'})[0].value == 'True'
        self.autoplay = Setting.objects.get_or_create(key='autoplay', defaults={'value': 'False'})[0].value == 'True'

        self.musiq = musiq
        self.queue = models.QueuedSong.objects
        Player.queue_semaphore = Semaphore(self.queue.count())
        self.alarm_playing = Event()
        self.running = True

        self.player = MopidyAPI()
        self.player_lock = Lock()
        with self.mopidy_command(important=True):
            self.player.playback.stop()
            self.player.tracklist.clear()
            # make songs disappear from tracklist after being played
            self.player.tracklist.set_consume(True)

        with self.mopidy_command(important=True):
            #currentsong = self.player.currentsong()
            self.volume = self.player.mixer.get_volume() / 100

    def start(self):
        self._loop()

    def progress(self):
        # the state is either pause or stop
        current_position = 0
        duration = 1
        with self.mopidy_command() as allowed:
            if allowed:
                current_position = self.player.playback.get_time_position()
                current_track = self.player.playback.get_current_track()
                if current_track is None:
                    return 0
                duration = current_track.length
        return 100 * current_position / duration
    def paused(self):
        # the state is either pause or stop
        paused = False
        with self.mopidy_command() as allowed:
            if allowed:
                paused = self.player.playback.get_state() != mopidy.core.PlaybackState.PLAYING
        return paused

    @background_thread
    def _loop(self):
        while True:

            catch_up = None
            if models.CurrentSong.objects.exists():
                # recover interrupted song from database
                current_song = models.CurrentSong.objects.get()

                # continue with the current song (approximately) where we last left
                song_provider = SongProvider.create(self.musiq, external_url=current_song.external_url)
                duration = song_provider.get_metadata()['duration']
                catch_up = round((timezone.now() - current_song.created).total_seconds() * 1000)
                if catch_up > duration * 1000:
                    catch_up = -1
            else:
                self.queue_semaphore.acquire()
                if not self.running:
                    break

                # select the next song depending on settings
                if self.musiq.base.settings.voting_system:
                    with transaction.atomic():
                        song = self.queue.all().order_by('-votes', 'index')[0]
                        song_id = song.id
                        self.queue.remove(song.id)
                elif self.shuffle:
                    index = random.randint(0,models.QueuedSong.objects.count() - 1)
                    song_id = models.QueuedSong.objects.all()[index].id
                    song = self.queue.remove(song_id)
                else:
                    # move the first song in the queue into the current song
                    song_id, song = self.queue.dequeue()

                if song is None:
                    # either the semaphore didn't match up with the actual count of songs in the queue or a race condition occured
                    self.musiq.base.logger.info('dequeued on empty list')
                    continue
                

                current_song = models.CurrentSong.objects.create(
                        queue_key=song_id,
                        manually_requested=song.manually_requested,
                        votes=song.votes,
                        internal_url=song.internal_url,
                        external_url=song.external_url,
                        artist=song.artist,
                        title=song.title,
                        duration=song.duration,
                )

                self._handle_autoplay()

                try:
                    archived_song = models.ArchivedSong.objects.get(url=current_song.external_url)
                    if self.musiq.base.settings.voting_system:
                        votes = current_song.votes
                    else:
                        votes = None
                    if self.musiq.base.settings.logging_enabled:
                        models.PlayLog.objects.create(
                                song=archived_song,
                                manually_requested=current_song.manually_requested,
                                votes=votes)
                except (models.ArchivedSong.DoesNotExist, models.ArchivedSong.MultipleObjectsReturned):
                    pass

            self.musiq.update_state()

            playing = Event()
            @self.player.on_event('playback_state_changed')
            def on_playback_state_changed(event):
                playing.set()

            with self.mopidy_command(important=True):
                # after a restart consume may be set to False again, so make sure it is on
                self.player.tracklist.clear()
                self.player.tracklist.set_consume(True)
                self.player.tracklist.add(uris=[current_song.internal_url])
                self.player.playback.play()
                # mopidy can only seek when the song is playing
                playing.wait(timeout=1)
                if catch_up is not None and catch_up >= 0:
                    self.player.playback.seek(catch_up)

            self.musiq.update_state()

            if catch_up is None or catch_up >= 0:
                if not self._wait_until_song_end():
                    # there was a ConnectionError during waiting for the song to end
                    # thus, we do not delete the current song but recover its state by restarting the loop
                    continue

            current_song.delete()

            if self.repeat:
                song_provider = SongProvider.create(self.musiq, external_url=current_song.external_url)
                self.queue.enqueue(song_provider.get_metadata(), False)
                self.queue_semaphore.release()
            else:
                # the song left the queue, we can delete big downloads
                song_utils.decide_deletion(current_song.internal_url)

            self.musiq.update_state()

            if self.musiq.base.user_manager.partymode_enabled() and random.random() < self.musiq.base.settings.alarm_probability:
                self.alarm_playing.set()
                self.musiq.base.lights.alarm_started()

                self.musiq.update_state()

                with self.mopidy_command(important=True):
                    self.player.tracklist.add(uris=['file://'+os.path.join(settings.BASE_DIR, 'config/sounds/alarm.m4a')])
                    self.player.playback.play()
                playing.clear()
                playing.wait(timeout=1)
                self._wait_until_song_end()

                self.musiq.base.lights.alarm_stopped()
                self.musiq.update_state()
                self.alarm_playing.clear()

    def _wait_until_song_end(self):
        # wait until the song is over. Returns True when finished without errors, False otherwise
        '''playback_ended = Event()
        @self.player.on_event('tracklist_changed')
        def on_tracklist_change(event):
            playback_ended.set()
        playback_ended.wait()'''
        error = False
        while True:
            with self.mopidy_command() as allowed:
                if allowed:
                    try:
                        if self.player.playback.get_state() == mopidy.core.PlaybackState.STOPPED:
                            break
                    except (ConnectionError, MopidyError) as e:
                        # error during state get, skip until reconnected
                        error = True
            time.sleep(0.1)
        return not error

    def _handle_autoplay(self, url=None):
        if self.autoplay and models.QueuedSong.objects.count() == 0:
            if url is None:
                # if no url was specified, use the one of the current song
                try:
                    current_song = models.CurrentSong.objects.get()
                    url = current_song.external_url
                except (models.CurrentSong.DoesNotExist, models.CurrentSong.MultipleObjectsReturned):
                    return

            provider = SongProvider.create(self.musiq, external_url=url)
            try:
                suggestion = provider.get_suggestion()
            except Exception as e:
                self.musiq.base.logger.error('error during suggestions for ' + url)
                self.musiq.base.logger.error(e)
            else:
                self.musiq._request_music('', suggestion, None, False, provider.type, archive=False, manually_requested=False)


    # wrapper method for our mopidy client that pings the mopidy server before any command and reconnects if necessary.
    @contextmanager
    def mopidy_command(self, important=False):
        timeout = 3
        if important:
            timeout = -1
        if self.player_lock.acquire(timeout=timeout):
            yield True
            self.player_lock.release()
        else:
            print('mopidy command could not be executed')
            yield False

    # every control changes the views state and returns an empty response
    def control(func):
        def _decorator(self, request, *args, **kwargs):
            # don't allow controls during alarm
            if self.alarm_playing.is_set():
                return HttpResponseBadRequest()
            func(self, request, *args, **kwargs)
            self.musiq.update_state()
            return HttpResponse()
        return wraps(func)(_decorator)
    # in the voting system only the admin can control the player
    def disabled_when_voting(func):
        def _decorator(self, request, *args, **kwargs):
            if self.musiq.base.settings.voting_system and not self.musiq.base.user_manager.has_controls(request.user):
                return HttpResponseForbidden()
            func(self, request, *args, **kwargs)
            self.musiq.update_state()
            return HttpResponse()
        return wraps(func)(_decorator)

    @disabled_when_voting
    @control
    def restart(self, request):
        with self.mopidy_command() as allowed:
            if allowed:
                self.player.playback.seek(0)
    @disabled_when_voting
    @control
    def seek_backward(self, request):
        with self.mopidy_command() as allowed:
            if allowed:
                current_position = self.player.playback.get_time_position()
                self.player.playback.seek(current_position - self.SEEK_DISTANCE)
    @disabled_when_voting
    @control
    def play(self, request):
        # unlikely race condition possible. but its impact is not worth the effort to prevent it
        with self.mopidy_command() as allowed:
            if allowed:
                self.player.playback.play()
    @disabled_when_voting
    @control
    def pause(self, request):
        with self.mopidy_command() as allowed:
            if allowed:
                self.player.playback.pause()
    @disabled_when_voting
    @control
    def seek_forward(self, request):
        with self.mopidy_command() as allowed:
            if allowed:
                current_position = self.player.playback.get_time_position()
                self.player.playback.seek(current_position + self.SEEK_DISTANCE)
    @disabled_when_voting
    @control
    def skip(self, request):
        with self.mopidy_command() as allowed:
            if allowed:
                self.player.playback.next()
    @disabled_when_voting
    @control
    def set_shuffle(self, request):
        enabled = request.POST.get('value') == 'true'
        Setting.objects.filter(key='shuffle').update(value=enabled)
        self.shuffle = enabled
    @disabled_when_voting
    @control
    def set_repeat(self, request):
        enabled = request.POST.get('value') == 'true'
        Setting.objects.filter(key='repeat').update(value=enabled)
        self.repeat = enabled
    @disabled_when_voting
    @control
    def set_autoplay(self, request):
        enabled = request.POST.get('value') == 'true'
        Setting.objects.filter(key='autoplay').update(value=enabled)
        self.autoplay = enabled
        self._handle_autoplay()
    @disabled_when_voting
    @control
    def set_volume(self, request):
        self.volume = float(request.POST.get('value'))
        with self.mopidy_command() as allowed:
            if allowed:
                self.player.mixer.set_volume(round(self.volume * 100))
    @disabled_when_voting
    @control
    def remove_all(self, request):
        if not self.musiq.base.user_manager.is_admin(request.user):
            return HttpResponseForbidden()
        with self.mopidy_command() as allowed:
            if allowed:
                with transaction.atomic():
                    count = self.queue.count()
                    self.queue.all().delete()
                for _ in range(count):
                    self.queue_semaphore.acquire(blocking=False)
    @disabled_when_voting
    @control
    def prioritize(self, request):
        key = request.POST.get('key')
        if key is None:
            return HttpResponseBadRequest()
        key = int(key)
        self.queue.prioritize(key)
    @disabled_when_voting
    @control
    def remove(self, request):
        key = request.POST.get('key')
        if key is None:
            return HttpResponseBadRequest()
        key = int(key)
        try:
            removed = self.queue.remove(key)
            self.queue_semaphore.acquire(blocking=False)
            # if we removed a song and it was added by autoplay,
            # we want it to be the new basis for autoplay
            if not removed.manually_requested:
                self._handle_autoplay(removed.external_url)
            else:
                self._handle_autoplay()
        except models.QueuedSong.DoesNotExist:
            return HttpResponseBadRequest('song does not exist')
    @disabled_when_voting
    @control
    def reorder(self, request):
        prev = request.POST.get('prev')
        key = request.POST.get('element')
        next = request.POST.get('next')
        if key is None or len(key) == 0:
            return HttpResponseBadRequest()
        if prev is None or len(prev) == 0:
            prev = None
        else:
            prev = int(prev)
        key = int(key)
        if next is None or len(next) == 0:
            next = None
        else:
            next = int(next)
        try:
            self.queue.reorder(prev, key, next)
        except ValueError:
            return HttpResponseBadRequest('request on old state')
    @control
    def vote_up(self, request):
        key = request.POST.get('key')
        if key is None:
            return HttpResponseBadRequest()
        key = int(key)

        models.CurrentSong.objects.filter(queue_key=key).update(votes=F('votes')+1)

        self.queue.vote_up(key)
    @control
    def vote_down(self, request):
        key = request.POST.get('key')
        if key is None:
            return HttpResponseBadRequest()
        key = int(key)

        models.CurrentSong.objects.filter(queue_key=key).update(votes=F('votes')-1)
        try:
            current_song = models.CurrentSong.objects.get()
            if current_song.queue_key == key and current_song.votes <= -self.musiq.base.settings.downvotes_to_kick:
                with self.mopidy_command() as allowed:
                    if allowed:
                        self.player.playback.next()
        except models.CurrentSong.DoesNotExist:
            pass

        removed = self.queue.vote_down(key, -self.musiq.base.settings.downvotes_to_kick)
        # if we removed a song by voting, and it was added by autoplay,
        # we want it to be the new basis for autoplay
        if removed is not None:
            self.queue_semaphore.acquire(blocking=False)
            if not removed.manually_requested:
                self._handle_autoplay(removed.external_url)
            else:
                self._handle_autoplay()

    @control
    def start_loop(self, request):
        if not self.musiq.base.user_manager.is_admin(request.user):
            return HttpResponseForbidden()
        if self.running:
            return HttpResponse()
        # start the main loop, only used for tests
        self.running = True
        self.start()
    @control
    def stop_loop(self, request):
        if not self.musiq.base.user_manager.is_admin(request.user):
            return HttpResponseForbidden()
        # stop the main loop, only used for tests
        self.running = False
        self.queue_semaphore.release()
