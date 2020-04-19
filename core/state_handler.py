"""This module handles realtime communication via websockets."""
import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer
from django.http import JsonResponse


def send_state_event(state):
    """Sends the given dictionary as a state update to all connected clients."""
    data = {
        "type": "state_update",
        "state": state,
    }
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("state", data)


class Stateful:
    """A base class for all classes with a state that should be updated in real time."""

    def state_dict(self):
        """Returns a dictionary containing all state of this class."""
        raise NotImplementedError()

    def get_state(self, _request):
        """Returns the state of this class as a json dictionary for clients to use."""
        state = self.state_dict()
        return JsonResponse(state)

    def update_state(self):
        """Sends an update event to all connected clients."""
        send_state_event(self.state_dict())


class StateConsumer(WebsocketConsumer):
    """Handles connections with websocket clients."""

    def connect(self):
        async_to_sync(self.channel_layer.group_add)("state", self.channel_name)
        self.accept()

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)("state", self.channel_name)

    def receive(self, text_data=None, bytes_data=None):
        pass

    # Receive message from room group
    def state_update(self, event):
        """Receives a message from the room group and sends it back to the websocke."""
        # Send message to WebSocket
        self.send(text_data=json.dumps(event["state"]))
