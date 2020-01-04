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
import core.musiq.youtube as youtube

from threading import Semaphore
from threading import Lock
from threading import Event
from threading import Thread
from datetime import datetime
from functools import wraps
from contextlib import contextmanager
import os
import mpd
import time
import random

class Player:
    queue_semaphore = None

    def __init__(self, musiq):
        self.SEEK_DISTANCE = 10
        self.shuffle = Setting.objects.get_or_create(key='shuffle', defaults={'value': False})[0].value == 'True'
        self.repeat = Setting.objects.get_or_create(key='repeat', defaults={'value': False})[0].value == 'True'
        self.autoplay = Setting.objects.get_or_create(key='autoplay', defaults={'value': False})[0].value == 'True'

        self.musiq = musiq
        self.queue = models.QueuedSong.objects
        Player.queue_semaphore = Semaphore(self.queue.count())
        self.alarm_playing = Event()

        self.player = mpd.MPDClient()
        self.player_lock = Lock()
        with self.mpd_command(important=True):
            self.player.clear()

        with self.mpd_command(important=True):
            status = self.player.status()
            currentsong = self.player.currentsong()
            self.volume = int(status['volume']) / 100

    def start(self):
        Thread(target=self._loop, daemon=True).start()

    def progress(self):
        # the state is either pause or stop
        status = {}
        currentsong = {}
        with self.mpd_command() as allowed:
            if allowed:
                status = self.player.status()
                currentsong = self.player.currentsong()
        if 'elapsed' not in status or 'time' not in currentsong:
            return 0
        return 100 * float(status['elapsed']) / float(currentsong['time'])
    def paused(self):
        # the state is either pause or stop
        paused = False
        with self.mpd_command() as allowed:
            if allowed:
                paused = self.player.status()['state'] != 'play'
        return paused

    def _loop(self):
        while True:

            catch_up = None
            if models.CurrentSong.objects.exists():
                # recover interrupted song from database
                current_song = models.CurrentSong.objects.get()

                # continue with the current song (approximately) where we last left
                duration = song_utils.get_duration(current_song.location)
                catch_up = (timezone.now() - current_song.created).total_seconds()
            else:
                self.queue_semaphore.acquire()

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
                
                location = song_utils.path_from_url(song.url)
                current_song = models.CurrentSong.objects.create(
                        queue_key=song_id,
                        manually_requested=song.manually_requested,
                        votes=song.votes,
                        url=song.url,
                        artist=song.artist,
                        title=song.title,
                        duration=song.duration,
                        location=location)

                self._handle_autoplay()

                try:
                    archived_song = models.ArchivedSong.objects.get(url=current_song.url)
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
        
            with self.mpd_command(important=True):
                self.player.add('file://' + current_song.location)
                self.player.play()
                if catch_up is not None:
                    self.player.seekcur(catch_up)
            self.musiq.update_state()

            self._wait_until_song_end()

            with self.mpd_command(important=True):
                try:
                    self.player.delete(0)
                except mpd.base.CommandError:
                    # catch Bad song index if there is no song
                    pass
            current_song.delete()

            if self.repeat:
                self.queue.enqueue(current_song.location, current_song.manually_requested)
                self.queue_semaphore.release()
            else:
                # the song left the queue, we can delete big downloads
                song_utils.decide_deletion(current_song.location)

            self.musiq.update_state()

            if self.musiq.base.user_manager.partymode_enabled() and random.random() < self.musiq.base.settings.alarm_probability:
                self.alarm_playing.set()
                self.musiq.base.lights.alarm_started()

                with self.mpd_command(important=True):
                    self.player.add('file://'+os.path.join(settings.BASE_DIR, 'config/sounds/alarm.m4a'))
                    self.player.play()
                self._wait_until_song_end()

                self.musiq.base.lights.alarm_stopped()
                with self.mpd_command(important=True):
                    self.player.delete(0)
                self.alarm_playing.clear()

    def _wait_until_song_end(self):
        # wait until the song is over
        while True:
            with self.mpd_command() as allowed:
                if allowed:
                    try:
                        if self.player.status()['state'] == 'stop':
                            break
                    except mpd.base.ConnectionError:
                        pass
            time.sleep(0.1) 

    def _handle_autoplay(self, url=None):
        if self.autoplay and models.QueuedSong.objects.count() == 0:
            if url is None:
                # if no url was specified, use the one of the current song
                try:
                    current_song = models.CurrentSong.objects.get()
                    url = current_song.url
                except (models.CurrentSong.DoesNotExist, models.CurrentSong.MultipleObjectsReturned):
                    return

            try:
                suggestion = youtube.get_suggestion(url)
            except Exception as e:
                self.musiq.base.logger.error('error during suggestions for ' + url)
                self.musiq.base.logger.error(e)
            else:
                self.musiq.request_song(
                        None,
                        suggestion, 
                        self.musiq.song_provider.check_new_song_accessible,
                        self.musiq.song_provider.get_new_song_location,
                        suggestion,
                        archive=False)



    # wrapper method for our mpd client that pings the mpd server before any command and reconnects if necessary. also catches protocol errors
    @contextmanager
    def mpd_command(self, important=False):
        timeout = 3
        if important:
            timeout = -1
        if self.player_lock.acquire(timeout=timeout):
            try:
                self.player.ping()
            except (mpd.base.ConnectionError, ConnectionResetError):
                for _ in range(5):
                    try:
                        self.player.connect('/var/run/mpd/socket', 6600)
                        break
                    except FileNotFoundError:
                        # system mpd is not running, try user mpd
                        try:
                            self.player.connect(os.path.expanduser('~/.mpd/socket'), 6600)
                        except mpd.base.ConnectionError:
                            # Already connected
                            break
                    except mpd.base.ConnectionError:
                        # Already connected
                        break
                    except (ConnectionResetError, ConnectionRefusedError):
                        time.sleep(0.5)
            except mpd.base.ProtocolError as e:
                print('protocol error during ping, continuing')
                print(e)
                pass
            try:
                yield True
            except mpd.base.ProtocolError as e:
                print(e)
                raise e
            finally:
                self.player_lock.release()
        else:
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
        with self.mpd_command() as allowed:
            if allowed:
                if self.player.status()['state'] != 'stop':
                    self.player.seekcur(0)
    @disabled_when_voting
    @control
    def seek_backward(self, request):
        with self.mpd_command() as allowed:
            if allowed:
                status = self.player.status()
                if 'elapsed' in status:
                    self.player.seekcur(float(status['elapsed']) - self.SEEK_DISTANCE)
    @disabled_when_voting
    @control
    def play(self, request):
        # unlikely race condition possible. but its impact is not worth the effort to prevent it
        with self.mpd_command() as allowed:
            if allowed:
                if self.player.status()['state'] == 'pause':
                    self.player.pause()
    @disabled_when_voting
    @control
    def pause(self, request):
        with self.mpd_command() as allowed:
            if allowed:
                if self.player.status()['state'] == 'play':
                    self.player.pause()
    @disabled_when_voting
    @control
    def seek_forward(self, request):
        with self.mpd_command() as allowed:
            if allowed:
                status = self.player.status()
                if 'elapsed' in status:
                    self.player.seekcur(float(status['elapsed']) + self.SEEK_DISTANCE)
    @disabled_when_voting
    @control
    def skip(self, request):
        with self.mpd_command() as allowed:
            if allowed:
                self.player.stop()
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
        with self.mpd_command() as allowed:
            if allowed:
                try:
                    self.player.setvol(round(self.volume * 100))
                except mpd.base.CommandError:
                    # sometimes the volume can't be set
                    self.musiq.base.logger.info('could not set volume')
                    pass
    @disabled_when_voting
    @control
    def remove_all(self, request):
        if not self.musiq.base.user_manager.is_admin(request.user):
            return HttpResponseForbidden()
        with self.mpd_command() as allowed:
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
                self._handle_autoplay(removed.url)
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
                with self.mpd_command() as allowed:
                    if allowed:
                        self.player.stop()
        except models.CurrentSong.DoesNotExist:
            pass

        removed = self.queue.vote_down(key, -self.musiq.base.settings.downvotes_to_kick)
        # if we removed a song by voting, and it was added by autoplay,
        # we want it to be the new basis for autoplay
        if removed is not None:
            self.queue_semaphore.acquire(blocking=False)
            if not removed.manually_requested:
                self._handle_autoplay(removed.url)
            else:
                self._handle_autoplay()
