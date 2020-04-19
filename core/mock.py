"""This module provides a minimal index method to have the server start up
without loading all dependencies and starting background threads."""

from django.http import HttpResponse


def index(_request):
    """Returns an information about the mock status."""
    return HttpResponse("You started the server with DJANGO_MOCK")
