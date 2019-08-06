from django.db import transaction
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.http import JsonResponse
from django.http import HttpResponseBadRequest

from core import models
import core.state_handler as state_handler

class Pad:

    def __init__(self, base):
        self.base = base

    def state_dict(self):
        state_dict = self.base.state_dict()
        state_dict['pad_version'] = models.Pad.objects.get(id=1).version
        return state_dict

    def get_state(self, request):
        state = self.state_dict()
        return JsonResponse(state)

    def update_state(self):
        state_handler.update_state(self.state_dict())

    def index(self, request):
        if not self.base.user_manager.has_pad(request.user):
            raise PermissionDenied
        context = self.base.context(request)

        pad = models.Pad.objects.get_or_create(id=1, defaults={'content': '', 'version': 0})[0]
        context['pad_version'] = pad.version
        context['pad_content'] = pad.content
        return render(request, 'pad.html', context)

    def submit(self, request):
        version = request.POST.get('version')
        content = request.POST.get('content')
        if version is None or version == '' or content is None:
            return HttpResponseBadRequest('No version or content supplied')
        try:
            version = int(version)
        except ValueError:
            return HttpResponseBadRequest('version is not a number')

        version_valid = True
        with transaction.atomic():
            pad = models.Pad.objects.get(id=1)
            current_version = pad.version
            if current_version == version:
                version_valid = True
                pad.version += 1
                pad.content = content
                pad.save()
            else:
                version_valid = False

        if version_valid:
            self.update_state()
            return HttpResponse('Updated Pad')
        else:
            return HttpResponseBadRequest('The content was changed in the meantime, please reload')
