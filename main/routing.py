"""This module registers the core apps websocket patterns."""

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import core.routing

APPLICATION = ProtocolTypeRouter(
    {"websocket": AuthMiddlewareStack(URLRouter(core.routing.WEBSOCKET_URLPATTERNS))}
)
