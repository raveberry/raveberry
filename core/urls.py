"""This module contains all url endpoints and maps them to their corresponding functions."""
import inspect

from typing import Any, List, get_type_hints

from django.core.handlers.wsgi import WSGIRequest
from django.urls import include, URLPattern
from django.urls import path
from django.views.generic import RedirectView

from core import mock
from main import settings

from core.base import Base

BASE = Base()

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="musiq", permanent=False), name="base"),
    path("musiq/", BASE.musiq.index, name="musiq"),
    path("lights/", BASE.lights.index, name="lights"),
    path("stream/", BASE.no_stream, name="no-stream"),
    path("network_info/", BASE.network_info.index, name="network-info"),
    path("settings/", BASE.settings.index, name="settings"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("login/", RedirectView.as_view(pattern_name="login", permanent=False)),
    path("logged_in/", BASE.logged_in, name="logged-in"),
    path("logout/", RedirectView.as_view(pattern_name="logout", permanent=False)),
    path(
        "api/",
        include(
            [
                path(
                    "musiq/",
                    include([path("post_song/", BASE.api.post_song, name="post-song")]),
                )
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
        for name, method in inspect.getmembers(obj, inspect.ismethod):
            if name == "get_state":
                # the state url is an exception
                # it cannot be named after its method name, as every page has its own get_state
                continue
            if name.startswith("_"):
                # do not expose internal methods
                continue
            type_hints = get_type_hints(method)
            if "request" in type_hints:
                request_type = type_hints["request"]
            elif "_request" in type_hints:
                request_type = type_hints["_request"]
            else:
                continue
            if issubclass(request_type, WSGIRequest) and method not in urlmethods:
                name = name.replace("_", "-")
                paths.append(path(name + "/", method, name=name))
    return paths


base_paths = get_paths([BASE])
BASE.urlpatterns = base_paths
musiq_paths = get_paths([BASE.musiq, BASE.musiq.controller, BASE.musiq.suggestions])
BASE.musiq.urlpatterns = musiq_paths
lights_paths = get_paths([BASE.lights.controller])
BASE.lights.urlpatterns = lights_paths
settings_paths = get_paths(
    [
        BASE.settings.basic,
        BASE.settings.platforms,
        BASE.settings.sound,
        BASE.settings.wifi,
        BASE.settings.library,
        BASE.settings.analysis,
        BASE.settings.system,
    ]
)
BASE.settings.urlpatterns = settings_paths

urlpatterns.append(
    path(
        "ajax/",
        include(
            [
                path("", include(base_paths)),
                path("musiq/state/", BASE.musiq.get_state, name="musiq-state"),
                path("musiq/", include(musiq_paths)),
                path("lights/state/", BASE.lights.get_state, name="lights-state"),
                path("lights/", include(lights_paths)),
                path("settings/state/", BASE.settings.get_state, name="settings-state"),
                path("settings/", include(settings_paths)),
            ]
        ),
    )
)

if settings.MOCK:
    for url in urlpatterns:
        if isinstance(url, URLPattern):
            url.callback = mock.index
else:
    BASE.start()
