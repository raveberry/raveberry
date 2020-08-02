"""This module handles the Neopixel led ring."""
from typing import List, Tuple

from core.lights.device import Device


class Ring(Device):
    """This class provides an interface to control the led ring."""

    # LED ring configuration:
    LED_COUNT = 16  # Number of LED pixels.
    LED_PIN = 10  # GPIO pin used. 10: SPI, 18: PWM (used for sound)
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 10  # DMA channel to use for generating signal (try 10)
    LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
    LED_INVERT = False  # True inverts the signal (when using NPN level shift)
    LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53

    LED_OFFSET = 12  # at which index the zeroth pixel is located.

    def __init__(self, lights) -> None:
        super().__init__(lights, "ring")

        try:
            import rpi_ws281x
        except ModuleNotFoundError:
            self.initialized = False
            return

        self.controller = rpi_ws281x.Adafruit_NeoPixel(
            self.LED_COUNT,
            self.LED_PIN,
            self.LED_FREQ_HZ,
            self.LED_DMA,
            self.LED_INVERT,
            self.LED_BRIGHTNESS,
            self.LED_CHANNEL,
        )
        try:
            self.controller.begin()
            self.initialized = True
        except RuntimeError:
            # could not connect to led ring
            self.initialized = False

    def set_colors(self, colors: List[Tuple[float, float, float]]) -> None:
        """Sets the colors of the ring to the given list of triples."""
        if not self.initialized:
            return
        for led in range(self.LED_COUNT):
            dimmed_color = (self.brightness * val for val in colors[led])
            scaled_color = tuple(int(val * 255) for val in dimmed_color)
            self.controller.setPixelColorRGB(
                (led + self.LED_OFFSET) % self.LED_COUNT, *scaled_color
            )
        self.controller.show()

    def clear(self) -> None:
        """Turns of all pixels by setting their color to black."""
        if not self.initialized:
            return
        for led in range(self.LED_COUNT):
            self.controller.setPixelColorRGB(led, 0, 0, 0)
        self.controller.show()
