from django.conf.urls import url
from core import state_handler

websocket_urlpatterns = [
    url(r'^state/$', state_handler.StateConsumer),
]
