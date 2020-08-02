"""This module handles WLED."""
from typing import List, Tuple

import socket

from core import util
from core.lights.device import Device
from core.models import Setting
from main import settings


class WLED(Device):
    """This class provides an interface to control WLED."""

    def __init__(self, lights) -> None:
        super().__init__(lights, "wled")

        self.led_count = int(
            self.lights.base.settings.get_setting("wled_led_count", "10")
        )

        self.ip = self.lights.base.settings.get_setting("wled_ip", "")
        if not self.ip and not settings.MOCK:
            try:
                device = util.get_default_device()
                broadcast = util.broadcast_of_device(device)
                self.ip = broadcast
            except:
                # we don't want the startup to fail
                # just because the broadcast address could not be determined
                self.ip = "127.0.0.1"
            Setting.objects.filter(key="wled_ip").update(value=self.ip)
        self.port = int(self.lights.base.settings.get_setting("wled_port", "21324"))

        self.header = bytes(
            [
                2,  # DRGB protocol, we update every led every frame
                1,  # wait 1 second after the last packet until resuming normally
            ]
        )

        self.initialized = True

    def set_colors(self, colors: List[Tuple[float, float, float]]) -> None:
        """Sets the colors of the WLED to the given list of triples."""
        if not self.initialized:
            return
        color_bytes = bytes(
            [round(val * self.brightness * 255) for color in colors for val in color]
        )

        packet = self.header + color_bytes

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        # allow broadcast to reach multiple WLED
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, (self.ip, self.port))

    def clear(self) -> None:
        """Turns of all pixels by setting their color to black."""
        self.set_colors([(0, 0, 0) for _ in range(self.led_count)])
