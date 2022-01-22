"""This module contains all public api endpoints."""
import re

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from django.conf import settings as conf
from core.musiq import musiq
from core.musiq.music_provider import ProviderError


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

    try:
        providers = musiq.get_providers(query)
    except ProviderError as error:
        return HttpResponseBadRequest(str(error))
    provider = musiq.try_providers(request.session.session_key, providers)
    if provider.error:
        return HttpResponseBadRequest(provider.error)
    return HttpResponse(provider.ok_message)


def version(request: WSGIRequest) -> HttpResponse:
    """Return the version of the running instance."""

    return HttpResponse(f"Raveberry version {conf.VERSION}")
