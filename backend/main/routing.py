"""This module registers the core apps websocket patterns."""

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

import core.routing

APPLICATION = ProtocolTypeRouter(
    {
        "websocket": AuthMiddlewareStack(URLRouter(core.routing.WEBSOCKET_URLPATTERNS)),
        # using django's asgi application for http requests allows async processing
        # since django 4.0 due to context aware sync_to_async
        # https://github.com/django/django/pull/13882
        "http": get_asgi_application(),
    }
)
