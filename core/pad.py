"""This module contains the pad."""

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.shortcuts import render

from core import models
from core.state_handler import Stateful


class Pad(Stateful):
    """This class handles requests on the /pad page."""

    def __init__(self, base):
        self.base = base

    def state_dict(self):
        state_dict = self.base.state_dict()
        state_dict["pad_version"] = models.Pad.objects.get(id=1).version
        return state_dict

    def index(self, request):
        """Renders the /pad page."""
        if not self.base.user_manager.has_pad(request.user):
            raise PermissionDenied
        context = self.base.context(request)

        pad = models.Pad.objects.get_or_create(
            id=1, defaults={"content": "", "version": 0}
        )[0]
        context["pad_version"] = pad.version
        context["pad_content"] = pad.content
        return render(request, "pad.html", context)

    def submit(self, request):
        """Stores a new version of the pad content.
        Makes sure that no conflicts occur."""
        version = request.POST.get("version")
        content = request.POST.get("content")
        if version is None or version == "" or content is None:
            return HttpResponseBadRequest("No version or content supplied")
        try:
            version = int(version)
        except ValueError:
            return HttpResponseBadRequest("version is not a number")

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

        if not version_valid:
            return HttpResponseBadRequest(
                "The content was changed in the meantime, please reload"
            )
        self.update_state()
        return HttpResponse("Updated Pad")
