from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

import json
import time

from threading import Thread

def update_state(state):
    data = {
        'type': 'state_update',
        'state': state,
    }
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'state',
        data
    )

class StateConsumer(WebsocketConsumer):
    def connect(self):
        async_to_sync(self.channel_layer.group_add)('state', self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)('state', self.channel_name)

    def receive(self, text_data):
        pass

    # Receive message from room group
    def state_update(self, event):
        # Send message to WebSocket
        self.send(text_data=json.dumps(event['state']))
