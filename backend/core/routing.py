"""This module defines the routing for realtime websocket requests."""

from django.urls import path
from core import state_handler

WEBSOCKET_URLPATTERNS = [path("state/", state_handler.StateConsumer.as_asgi())]
