"""This module manages and counts user accesses and handles permissions."""
import re
from ast import literal_eval
import colorsys
import random
import time
from functools import wraps
from typing import Callable, Optional

import ipware
from django.contrib.sessions.models import Session
from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone

from core import redis

# kick users after some time without any request
from core.lights import leds
from core.settings import storage
from core.settings.storage import Privileges
from core.util import extract_value

INACTIVITY_PERIOD = 600


def has_controls(user) -> bool:
    """Determines whether the given user is allowed to control playback."""
    return user.username == "mod" or is_admin(user)


def is_admin(user) -> bool:
    """Determines whether the given user is the admin."""
    return user.is_superuser


def has_privilege(user, privilege: Privileges):
    if privilege == Privileges.everybody:
        return True
    elif privilege == Privileges.mod and has_controls(user):
        return True
    elif privilege == Privileges.admin and is_admin(user):
        return True
    return False


def update_user_count() -> None:
    """Go through all recent requests and delete those that were too long ago."""
    now = time.time()
    last_requests = redis.get("last_requests")
    for key, value in list(last_requests.items()):
        if now - value >= INACTIVITY_PERIOD:
            del last_requests[key]
            redis.put("last_requests", last_requests)
    redis.put("last_user_count_update", now)


def get_count() -> int:
    """Returns the number of currently active users.
    Updates this number after an intervals since the last update."""
    if time.time() - redis.get("last_user_count_update") >= 60:
        update_user_count()
    return len(redis.get("last_requests"))


def partymode_enabled() -> bool:
    """Determines whether partymode is enabled,
    based on the number of currently active users."""
    return len(redis.get("last_requests")) >= storage.get("people_to_party")


def get_client_ip(request: WSGIRequest):
    """Returns the origin IP of a given request or "" if not possible."""
    request_ip, _ = ipware.get_client_ip(request)
    if request_ip is None:
        request_ip = ""
    return request_ip


def try_vote(request_ip: str, queue_key: int, amount: int) -> bool:
    """If the user can not vote any more for the song into the given direction, return False.
    Otherwise, perform the vote and returns True."""
    # Votes are stored as individual (who, what) tuples in redis.
    # A mapping who -> [what, ...] is not used,
    # because each modification would require deserialization and subsequent serialization.
    # Without such a mapping we cannot easily find all votes belonging to a session key,
    # which would be required to update the view of a user whose client-votes got desynced.
    # This should never happen during normal usage, so we optimize for our main use case:
    # looking up whether a single user voted for a single song, which is constant with tuples.
    # Since this feature indexes by the request IP and not the session_key,
    # it can not share its data structure with the votes for the color indicators.
    entry = str((request_ip, queue_key))
    allowed = True

    # redis transaction: https://github.com/Redis/redis-py#pipelines
    def check_entry(pipe) -> None:
        nonlocal allowed
        vote = pipe.get(entry)
        if vote is None:
            new_vote = amount
        else:
            new_vote = int(vote) + amount
        if new_vote < -1 or new_vote > 1:
            allowed = False
            return
        allowed = True
        # expire these entries to avoid accumulation over long runtimes.
        pipe.multi()
        pipe.set(entry, new_vote, ex=24 * 60 * 60)

    redis.connection.transaction(check_entry, entry)
    return allowed


def _get_next_color():
    with transaction.atomic():
        next_index = storage.get("next_color_index")
        storage.put("next_color_index", next_index + 1)

    offset = storage.get("color_offset")

    hue = offset + next_index * (137.508 / 360)  # approximation for the golden angle
    color = colorsys.hsv_to_rgb(hue, 0.4, 1)

    return "#%02x%02x%02x" % tuple(round(v * 255) for v in color)


def color_of(session_key: str) -> Optional[str]:
    if not session_key or storage.get("color_indication") == storage.Privileges.nobody:
        return None
    # no transaction because this is called many times and at worst race conditions would result
    # in a different color being set
    color = redis.connection.get("color-" + session_key)
    if color is None:
        color = _get_next_color()
    # TODO: this is lost on server restart.
    # maybe store the color client side so it can be recovered?
    redis.connection.set("color-" + session_key, color, ex=24 * 60 * 60)
    return color


def register_song(request: WSGIRequest, queue_key: int) -> None:
    # For each song, identified by its queue_key, the following information is stored:
    # (<session_key>, {<session_key>: <vote>, …})
    # This requires a session_key, thus it can only be used in @tracked functions
    session_key = request.session.session_key

    key = f"engagement-{queue_key}"

    def update_entry(pipe) -> None:
        value = pipe.get(key)
        engagement = None if value is None else literal_eval(value)
        if engagement is None:
            engagement = (None, {})
        _, votes = engagement
        # expire these entries to avoid accumulation over long runtimes.
        pipe.multi()
        pipe.set(key, str((session_key, votes)), ex=24 * 60 * 60)

    redis.connection.transaction(update_entry, key)


def register_vote(request: WSGIRequest, queue_key: int, amount: int) -> None:
    session_key = request.session.session_key

    key = f"engagement-{queue_key}"

    def update_entry(pipe) -> None:
        value = pipe.get(key)
        engagement = None if value is None else literal_eval(value)
        if engagement is None:
            engagement = (None, {})
        requested_by, votes = engagement
        if session_key in votes:
            votes[session_key] += amount
        else:
            votes[session_key] = amount
        # clamp votes to [-1,1]. This helps recovering from desyncs after redis was cleared
        # but client votes are still locked in
        votes[session_key] = max(-1, min(1, votes[session_key]))
        if votes[session_key] == 0:
            del votes[session_key]
        # expire these entries to avoid accumulation over long runtimes.
        pipe.multi()
        pipe.set(key, str((requested_by, votes)), ex=24 * 60 * 60)

    redis.connection.transaction(update_entry, key)


def set_user_color(request: WSGIRequest) -> HttpResponse:
    """Updates the color assigned to the session of the request."""
    from core.musiq import musiq

    color, response = extract_value(request.POST)
    if not color or not re.match(r"^#[0-9a-f]{6}$", color):
        return HttpResponseBadRequest()
    session_key = request.session.session_key
    redis.connection.set("color-" + session_key, color, ex=24 * 60 * 60)
    musiq.update_state()
    return response


def tracked(
    func: Callable[[WSGIRequest], HttpResponse]
) -> Callable[[WSGIRequest], HttpResponse]:
    """A decorator that stores the last access for every connected ip
    so the number of active users can be determined."""

    def _decorator(request: WSGIRequest) -> HttpResponse:
        # create a sessions if none exists (necessary for anonymous users)
        if not request.session or not request.session.session_key:
            # if there are no active sessions (= this is the first one)
            # reset the color index and choose a new offset.
            active_sessions = Session.objects.filter(
                expire_date__gte=timezone.now()
            ).count()
            if active_sessions == 0:
                storage.put("color_offset", random.random())
                storage.put("next_color_index", 0)

            request.session.save()

        request_ip = get_client_ip(request)
        last_requests = redis.get("last_requests")
        last_requests[request_ip] = time.time()
        redis.put("last_requests", last_requests)

        def check():
            active = redis.get("active_requests")
            if active > 0:
                leds.enable_act_led()
            else:
                leds.disable_act_led()

        redis.connection.incr("active_requests")
        check()
        response = func(request)
        redis.connection.decr("active_requests")
        check()

        return response

    return wraps(func)(_decorator)
