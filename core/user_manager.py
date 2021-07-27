"""This module manages and counts user accesses and handles permissions."""
import time
from typing import Any, Callable

import ipware
from django.contrib.auth.models import AbstractUser
from django.core.handlers.wsgi import WSGIRequest

import core.settings.storage as storage
from core import redis

# kick users after some time without any request
INACTIVITY_PERIOD = 600


def has_controls(user: AbstractUser) -> bool:
    """Determines whether the given user is allowed to control playback."""
    return user.username == "mod" or is_admin(user)


def is_admin(user: AbstractUser) -> bool:
    """Determines whether the given user is the admin."""
    return user.is_superuser


def update_user_count() -> None:
    """Go through all recent requests and delete those that were too long ago."""
    now = time.time()
    last_requests = redis.get("last_requests")
    for key, value in list(last_requests.items()):
        if now - value >= INACTIVITY_PERIOD:
            del last_requests[key]
            redis.set("last_requests", last_requests)
    redis.set("last_user_count_update", now)


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
    if not storage.get("logging_enabled"):
        return ""
    request_ip, _ = ipware.get_client_ip(request)
    if request_ip is None:
        request_ip = ""
    return request_ip


class SimpleMiddleware:
    """This middleware tracks stores the last access for every connected ip
    so the number of active users can be determined."""

    def __init__(self, get_response: Callable[[WSGIRequest], Any]) -> None:
        # One-time configuration and initialization.
        self.get_response = get_response

    def __call__(self, request: WSGIRequest) -> Any:
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        request_ip = get_client_ip(request)
        last_requests = redis.get("last_requests")
        last_requests[request_ip] = time.time()
        redis.set("last_requests", last_requests)

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
