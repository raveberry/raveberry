from typing import TYPE_CHECKING

import ipware
import re
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

if TYPE_CHECKING:
    from core.base import Base


class Api:
    def __init__(self, base: "Base") -> None:
        self.base = base

    @csrf_exempt
    def post_song(self, request: WSGIRequest) -> HttpResponse:
        """This endpoint is part of the API and exempt from CSRF checks.
        Shareberry uses this endpoint."""
        # only get ip on user requests
        if self.base.settings.basic.logging_enabled:
            request_ip, _ = ipware.get_client_ip(request)
            if request_ip is None:
                request_ip = ""
        else:
            request_ip = ""
        query = request.POST.get("query")
        if not query:
            return HttpResponseBadRequest("No query to share.")

        match = re.search("(?P<url>https?://[^\s]+)", query)
        if match:
            query = match.group("url")

        # Set the requested platform to 'spotify'.
        # It will automatically fall back to Youtube
        # if Spotify is not enabled or a youtube link was requested.
        successful, message, _ = self.base.musiq.do_request_music(
            request_ip, query, None, False, "spotify"
        )
        if not successful:
            return HttpResponseBadRequest(message)
        return HttpResponse(message)
