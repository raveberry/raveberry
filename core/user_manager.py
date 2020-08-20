"""This module manages and counts user accesses."""
from datetime import datetime
from typing import Any, Callable, Dict, TYPE_CHECKING

import ipware
from django.contrib.auth.models import AbstractUser
from django.core.handlers.wsgi import WSGIRequest
from django.utils import timezone


if TYPE_CHECKING:
    from core.base import Base


class UserManager:
    """This class counts active users and handles permissions."""

    def has_controls(self, user: AbstractUser) -> bool:
        """Determines whether the given user is allowed to control playback."""
        return user.username == "mod" or self.is_admin(user)

    @classmethod
    def is_admin(cls, user: AbstractUser) -> bool:
        """Determines whether the given user is the admin."""
        return user.is_superuser

    # This dictionary needs to be static so the middleware can access it.
    last_requests: Dict[str, datetime] = {}

    def __init__(self, base: "Base") -> None:
        self.base = base

        # kick users after some time without any request
        self.inactivity_period = 600
        self.last_user_count_update = timezone.now()
        self.update_user_count()

    def update_user_count(self) -> None:
        """Go through all recent requests and delete those that were too long ago."""
        now = timezone.now()
        for key, value in list(UserManager.last_requests.items()):
            if (now - value).seconds >= self.inactivity_period:
                del UserManager.last_requests[key]
        self.last_user_count_update = now

    def get_count(self) -> int:
        """Returns the number of currently active users.
        Updates this number after an intervals since the last update."""
        if (timezone.now() - self.last_user_count_update).seconds >= 60:
            self.update_user_count()
        return len(UserManager.last_requests)

    def partymode_enabled(self) -> bool:
        """Determines whether partymode is enabled,
        based on the number of currently active users."""
        return (
            len(UserManager.last_requests) >= self.base.settings.basic.people_to_party
        )


class SimpleMiddleware:
    """This middleware tracks stores the last access for every connected ip
    so the number of active users can be determined."""

    def __init__(self, get_response: Callable[[WSGIRequest], Any]) -> None:
        # One-time configuration and initialization.
        self.get_response = get_response

    def __call__(self, request: WSGIRequest) -> Any:
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        request_ip, _ = ipware.get_client_ip(request)
        if request_ip is None:
            request_ip = ""
        UserManager.last_requests[request_ip] = timezone.now()

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
