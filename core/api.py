"""This module contains all public api endpoints."""
import re
from django.conf import settings as conf
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

import core.settings.storage as storage
from core import user_manager
from core.musiq import musiq


@csrf_exempt
def post_song(request: WSGIRequest) -> HttpResponse:
    """This endpoint is part of the API and exempt from CSRF checks.
    Shareberry uses this endpoint."""
    # only get ip on user requests
    query = request.POST.get("query")
    if not query:
        return HttpResponseBadRequest("No query to share.")

    match = re.search(r"(?P<url>https?://[^\s]+)", query)
    if match:
        query = match.group("url")

    # Set the requested platform to 'spotify'.
    # It will automatically fall back to Youtube
    # if Spotify is not enabled or a youtube link was requested.
    successful, message, _ = musiq.do_request_music(
        request.session.session_key, query, None, False, "spotify"
    )
    if not successful:
        return HttpResponseBadRequest(message)
    return HttpResponse(message)


def version(request: WSGIRequest) -> HttpResponse:
    """Return the version of the running instance."""
    return HttpResponse(f"Raveberry version {conf.VERSION}")
