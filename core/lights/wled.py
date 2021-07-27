"""This module handles WLED."""
from typing import List, Tuple

import socket

from core import util, redis
from core.lights.device import Device
from core.settings import storage


class WLED(Device):
    """This class provides an interface to control WLED."""

    def __init__(self, manager) -> None:
        super().__init__(manager, "wled")

        self.led_count = storage.get("wled_led_count")

        self.ip = storage.get("wled_ip")
        if not self.ip:
            try:
                device = util.get_devices()[0]
                broadcast = util.broadcast_of_device(device)
                self.ip = broadcast
            except:
                # we don't want the startup to fail
                # just because the broadcast address could not be determined
                self.ip = "127.0.0.1"
            storage.set("wled_ip", self.ip)
        self.port = storage.get("wled_port")

        self.header = bytes(
            [
                2,  # DRGB protocol, we update every led every frame
                1,  # wait 1 second after the last packet until resuming normally
            ]
        )

        self.initialized = True
        redis.set("wled_initialized", True)

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
