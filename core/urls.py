"""This module contains all url endpoints and maps them to their corresponding functions."""
import inspect

from typing import Any, List

from django.core.handlers.wsgi import WSGIRequest
from django.urls import include, path, URLPattern
from django.views.generic import RedirectView

import core.api as api
import core.network_info as network_info
import core.base as base
import core.lights.lights as lights
import core.lights.controller as lights_controller
import core.musiq.musiq as musiq
import core.musiq.controller as musiq_controller
import core.musiq.suggestions as suggestions
import core.settings.settings as settings
import core.settings.analysis as analysis
import core.settings.basic as basic
import core.settings.library as library
import core.settings.platforms as platforms
import core.settings.sound as sound
import core.settings.system as system
import core.settings.wifi as wifi
from core import state_handler

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="musiq", permanent=False), name="base"),
    path("musiq/", musiq.index, name="musiq"),
    path("lights/", lights.index, name="lights"),
    path("stream/", base.no_stream, name="no-stream"),
    path("network-info/", network_info.index, name="network-info"),
    path("settings/", settings.index, name="settings"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("login/", RedirectView.as_view(pattern_name="login", permanent=False)),
    path("logged-in/", base.logged_in, name="logged-in"),
    path("logout/", RedirectView.as_view(pattern_name="logout", permanent=False)),
    path(
        "api/",
        include(
            [
                path("version/", api.version, name="version"),
                path(
                    "musiq/",
                    include(
                        [
                            path("post_song/", api.post_song, name="post_song"),
                            path("post-song/", api.post_song, name="post-song"),
                        ]
                    ),
                ),
            ]
        ),
    ),
]

urlmethods = [urlpattern.callback for urlpattern in urlpatterns]


def get_paths(objs: List[Any]) -> List[URLPattern]:
    """Iterates through the given objects and identifies all methods that serve http requests.
    A url pattern is generated for each of these methods,
    but only if no such path exists already in urlpatterns.
    Returns the list of url patterns."""
    paths = []
    for obj in objs:
        for name, method in inspect.getmembers(obj, inspect.isfunction):
            if name == "get_state":
                # the state url is an exception
                # it cannot be named after its method name, as every page has its own get_state
                continue
            if name.startswith("_"):
                # do not expose internal methods
                continue
            # use __annotations__ instead of get_type_hints, because the latter raised errors about
            # WSGIRequest not being defined in some configurations
            # string annotations are sufficient for our use case
            type_hints = method.__annotations__
            if "request" in type_hints:
                request_type = type_hints["request"]
            elif "_request" in type_hints:
                request_type = type_hints["_request"]
            else:
                continue
            if (
                request_type == "WSGIRequest" or issubclass(request_type, WSGIRequest)
            ) and method not in urlmethods:
                name = name.replace("_", "-")
                paths.append(path(name + "/", method, name=name))
    return paths


base_paths = get_paths([base])
musiq_paths = get_paths([musiq, musiq_controller, suggestions])
lights_paths = get_paths([lights_controller])
settings_paths = get_paths([basic, platforms, sound, wifi, library, analysis, system])

urlpatterns.append(
    path(
        "ajax/",
        include(
            [
                path("", include(base_paths)),
                path(
                    "musiq/state/",
                    state_handler.get_state,
                    {"module": musiq},
                    name="musiq-state",
                ),
                path("musiq/", include(musiq_paths)),
                path(
                    "lights/state/",
                    state_handler.get_state,
                    {"module": lights},
                    name="lights-state",
                ),
                path("lights/", include(lights_paths)),
                path(
                    "settings/state/",
                    state_handler.get_state,
                    {"module": settings},
                    name="settings-state",
                ),
                path("settings/", include(settings_paths)),
            ]
        ),
    )
)
