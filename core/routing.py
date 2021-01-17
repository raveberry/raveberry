"""This module defines the routing for realtime websocket requests."""

from django.conf.urls import url
from core import state_handler

WEBSOCKET_URLPATTERNS = [url(r"^state/$", state_handler.StateConsumer)]
