from django.conf import settings
from django.http import HttpResponse
from django.http import JsonResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.db import transaction
from django.urls import reverse

from core.settings import Settings
from core.musiq.musiq import Musiq
from core.lights.lights import Lights
from core.pad import Pad
from core.user_manager import UserManager
import core.models as models
import core.state_handler as state_handler

import os
import random
import logging

class Base:
    def __init__(self):
        self.logger = logging.getLogger('raveberry')
        self.settings = Settings(self)
        self.user_manager = UserManager(self)
        self.lights = Lights(self)
        self.pad = Pad(self)
        self.musiq = Musiq(self)

    def get_random_hashtag(self):
        if models.Tag.objects.count() == 0:
            return 'no hashtags present :('
        index = random.randint(0,models.Tag.objects.count() - 1)
        hashtag = models.Tag.objects.all()[index]
        return hashtag.text

    def increment_counter(self):
        with transaction.atomic():
            counter = models.Counter.objects.get_or_create(id=1, defaults={'value': 0})[0]
            counter.value += 1
            counter.save()
        self.update_state()
        return counter.value

    def _get_apk_link(self):
        local_apk = os.path.join(settings.STATIC_ROOT, 'apk/shareberry.apk')
        if os.path.isfile(local_apk):
            return os.path.join(settings.STATIC_URL, 'apk/shareberry.apk')
        else:
            return 'https://github.com/raveberry/shareberry/raw/master/app/release/shareberry.apk'

    def context(self, request):
        self.increment_counter()
        return {
            'voting_system': self.settings.voting_system,
            'hashtag': self.get_random_hashtag(),
            'controls_enabled': self.user_manager.has_controls(request.user),
            'pad_enabled': self.user_manager.has_pad(request.user),
            'is_admin': self.user_manager.is_admin(request.user),
            'apk_link': self._get_apk_link(),
            'spotify_enabled': self.settings.spotify_enabled
        }
    
    def state_dict(self):
        # this function constructs a base state dictionary with website wide state
        # pages sending states extend this state dictionary
        return {
            'partymode': self.user_manager.partymode_enabled(),
            'users': self.user_manager.get_count(),
            'visitors': models.Counter.objects.get_or_create(id=1, defaults={'value': 0})[0].value,
            'lights_enabled': self.lights.loop_active.is_set(),
            'alarm': self.musiq.player.alarm_playing.is_set(),
            'default_platform': 'spotify' if self.settings.spotify_enabled else 'youtube',
            }

    def get_state(self, request):
        state = self.state_dict()
        return JsonResponse(state)

    def update_state(self):
        state_handler.update_state(self.state_dict())

    def submit_hashtag(self, request):
        hashtag = request.POST.get('hashtag')
        if hashtag is None or len(hashtag) == 0:
            return HttpResponseBadRequest()

        if hashtag[0] != '#':
            hashtag = '#' + hashtag
        models.Tag.objects.create(text=hashtag)

        return HttpResponse()

    def logged_in(self, request):
        if request.user.username == 'admin':
            return HttpResponseRedirect(reverse('settings'))
        else:
            return HttpResponseRedirect(reverse('musiq'))
