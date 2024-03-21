"""This module provides common functionality for all pages on the site."""

import os
import random
from typing import Any, Dict

from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse

from django.conf import settings as conf
from core import models, redis, user_manager
from core.lights import controller
from core.musiq import musiq
from core.settings import storage
from core.settings import system
from core.state_handler import send_state


def _get_random_hashtag() -> str:
    active_hashtags = models.Tag.objects.filter(active=True)
    if active_hashtags.count() == 0:
        return "Add your first hashtag!"
    index = random.randint(0, active_hashtags.count() - 1)
    hashtag = active_hashtags[index]
    return hashtag.text


def _get_apk_link() -> str:
    local_apk = os.path.join(conf.STATIC_FILES, "apk/shareberry.apk")
    if os.path.isfile(local_apk):
        assert conf.STATIC_URL
        return os.path.join(conf.STATIC_URL, "apk/shareberry.apk")
    return "https://github.com/raveberry/shareberry/releases/latest/download/shareberry.apk"


def _increment_counter() -> int:
    with transaction.atomic():
        counter = models.Counter.objects.get_or_create(id=1, defaults={"value": 0})[0]
        counter.value += 1
        counter.save()
    update_state()
    return counter.value


def context(request: WSGIRequest) -> Dict[str, Any]:
    """Returns the base context that is needed on every page.
    Increments the visitors counter."""
    from core import urls

    _increment_counter()
    return {
        "base_urls": urls.base_paths,
        "interactivity": storage.get("interactivity"),
        "interactivities": {
            "fullControl": storage.Interactivity.full_control,
            "fullVoting": storage.Interactivity.full_voting,
            "upvotesOnly": storage.Interactivity.upvotes_only,
            "noControl": storage.Interactivity.no_control,
        },
        "color_indication": user_manager.has_privilege(
            request.user, storage.get("color_indication")
        ),
        # We pass the color to the user here for two reasons
        # 1. a color is assigned to every user on page load, not on first interaction
        # 2. during state updates every session receives all information,
        #    thus we would have to send the mapping to everyone, revealing session keys
        "user_color": user_manager.color_of(request.session.session_key),
        "privileges": {
            "everybody": storage.Privileges.everybody,
            "mod": storage.Privileges.mod,
            "admin": storage.Privileges.admin,
            "nobody": storage.Privileges.nobody,
        },
        "hashtag": _get_random_hashtag(),
        "demo": conf.DEMO,
        "controls_enabled": user_manager.has_controls(request.user)
        or storage.get("interactivity") == storage.Interactivity.full_control,
        "is_admin": user_manager.is_admin(request.user),
        "apk_link": _get_apk_link(),
        "local_enabled": storage.get("local_enabled"),
        "youtube_enabled": storage.get("youtube_enabled"),
        "spotify_enabled": storage.get("spotify_enabled"),
        "soundcloud_enabled": storage.get("soundcloud_enabled"),
        "jamendo_enabled": storage.get("jamendo_enabled"),
    }


def state_dict() -> Dict[str, Any]:
    """This function constructs a base state dictionary with website wide state.
    Pages sending states extend this state dictionary."""
    try:
        default_platform = musiq.enabled_platforms_by_priority()[0]
    except IndexError:
        default_platform = ""
    return {
        "partymode": user_manager.partymode_enabled(),
        "users": user_manager.get_count(),
        "visitors": models.Counter.objects.get_or_create(id=1, defaults={"value": 0})[
            0
        ].value,
        "lightsEnabled": redis.get("lights_active"),
        "playbackError": redis.get("playback_error"),
        "alarm": redis.get("alarm_playing"),
        "defaultPlatform": default_platform,
    }


def no_stream(request: WSGIRequest) -> HttpResponse:
    """Renders the /stream page. If this is reached, there is no stream active."""
    return render(request, "no_stream.html", context(request))


def submit_hashtag(request: WSGIRequest) -> HttpResponse:
    """Add the given hashtag to the database."""
    hashtag = request.POST.get("hashtag")
    if hashtag is None or len(hashtag) == 0:
        return HttpResponseBadRequest()

    if hashtag[0] != "#":
        hashtag = "#" + hashtag
    models.Tag.objects.create(text=hashtag, active=storage.get("hashtags_active"))

    return HttpResponse()


def logged_in(request: WSGIRequest) -> HttpResponse:
    """This endpoint is visited after every login.
    Redirect the admin to the settings and everybody else to the musiq page."""
    if user_manager.is_admin(request.user):
        return HttpResponseRedirect(reverse("settings"))
    return HttpResponseRedirect(reverse("musiq"))


def set_user_color(request: WSGIRequest) -> None:
    """Set user color for indication of votes.
    Situated in base because the dropdown is accessible from every page."""
    return user_manager.set_user_color(request)


def set_lights_shortcut(request: WSGIRequest) -> None:
    """Request endpoint for the lights shortcut.
    Situated in base because the dropdown is accessible from every page."""
    return controller.set_lights_shortcut(request)


def upgrade_available(_request: WSGIRequest) -> HttpResponse:
    """Checks whether newer Raveberry version is available."""
    latest_version = system.fetch_latest_version()
    current_version = conf.VERSION
    if latest_version and latest_version != current_version:
        return JsonResponse(True, safe=False)
    return JsonResponse(False, safe=False)


def update_state() -> None:
    """Sends an update event to all connected clients."""
    send_state(state_dict())
