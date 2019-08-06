from django.utils import timezone
from django.conf import settings

import core.models as models

import subprocess
import ipware

class UserManager:
    last_requests = {}

    def __init__(self, base):
        self.base = base

        # kick users after some time without any request
        self.inactivity_period = 600
        self.update_user_count()

    def update_user_count(self):
        now = timezone.now()
        for key, value in list(UserManager.last_requests.items()):
            if (now - value).seconds >= self.inactivity_period:
                del UserManager.last_requests[key]
        self.last_user_count_update = now
    
    def get_count(self):
        if (timezone.now() - self.last_user_count_update).seconds >= 60:
            self.update_user_count()
        return len(UserManager.last_requests)

    def partymode_enabled(self):
        return len(UserManager.last_requests) >= self.base.settings.people_to_party
    
    def has_controls(self, user):
        return user.username == 'mod' or \
                user.username == 'pad' or \
                user.username == 'admin'

    def has_pad(self, user):
        return user.username == 'pad' or \
                user.username == 'admin'

    def is_admin(self, user):
        return user.username == 'admin'

class SimpleMiddleware:
    def __init__(self, get_response):
        # One-time configuration and initialization.
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        ip, is_routable = ipware.get_client_ip(request)
        if ip is None:
            ip = ''
        UserManager.last_requests[ip] = timezone.now()

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
