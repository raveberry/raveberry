"""This module handles realtime communication via websockets."""
import json
from typing import Dict, Any

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer
from django.http import JsonResponse


def send_state_event(state: Dict[str, Any]) -> None:
    """Sends the given dictionary as a state update to all connected clients."""
    data = {
        "type": "state_update",
        "state": state,
    }
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("state", data)


class Stateful:
    """A base class for all classes with a state that should be updated in real time."""

    def state_dict(self) -> Dict[str, Any]:
        """Returns a dictionary containing all state of this class."""
        raise NotImplementedError()

    def get_state(self, _request) -> JsonResponse:
        """Returns the state of this class as a json dictionary for clients to use."""
        state = self.state_dict()
        return JsonResponse(state)

    def update_state(self) -> None:
        """Sends an update event to all connected clients."""
        send_state_event(self.state_dict())


class StateConsumer(WebsocketConsumer):
    """Handles connections with websocket clients."""

    def connect(self) -> None:
        async_to_sync(self.channel_layer.group_add)("state", self.channel_name)
        self.accept()

    def disconnect(self, code: int) -> None:
        async_to_sync(self.channel_layer.group_discard)("state", self.channel_name)

    def receive(self, text_data: str = None, bytes_data: bytes = None) -> None:
        pass

    # Receive message from room group
    def state_update(self, event: Dict[str, Any]):
        """Receives a message from the room group and sends it back to the websocket."""
        # Send message to WebSocket
        self.send(text_data=json.dumps(event["state"]))
