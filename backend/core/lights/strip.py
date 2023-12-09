"""This module handles the led strip."""
from typing import Tuple

from core import redis
from core.lights.device import Device


class Strip(Device):
    """This class provides an interface to control the led strip."""

    def __init__(self, manager) -> None:
        super().__init__(manager, "strip")
        self.monochrome = True

        try:
            # https://github.com/adafruit/Adafruit_CircuitPython_PCA9685/blob/main/examples/pca9685_simpletest.py
            from board import SCL, SDA
            import busio
            from adafruit_pca9685 import PCA9685
        except (ModuleNotFoundError, ImportError):
            # There is a problem with board.py installs, catch it with the ImportError
            return

        try:
            i2c_bus = busio.I2C(SCL, SDA)
            self.controller = PCA9685(i2c_bus)
            self.controller.frequency = 60

            self.initialized = True
            redis.put("strip_initialized", True)
        except ValueError:
            # LED strip is not connected
            return

    def set_color(self, color: Tuple[float, float, float]) -> None:
        """Sets the color of the strip to the given rgb triple."""
        if not self.initialized:
            return

        for channel, val in enumerate(color):
            dimmed_val = val * self.brightness
            scaled_val = round(dimmed_val * 4095)
            self.controller.channels[channel].duty_cycle = scaled_val

    def clear(self) -> None:
        """Turns off the strip by setting its color to black."""
        if not self.initialized:
            return

        for channel in range(3):
            self.controller.channels[channel].duty_cycle = 0
