"""This module contains all programs used for visualization (except complex screen programs)."""

from __future__ import annotations

import colorsys
import errno
import logging
import math
import os
import subprocess
from typing import Tuple, List, TYPE_CHECKING, cast, Optional

from django.conf import settings

if TYPE_CHECKING:
    from core.lights.lights import Lights


class VizProgram:
    """The base class for all programs."""

    def __init__(self, lights: "Lights") -> None:
        self.lights = lights
        self.consumers = 0
        self.name = "Unknown"

    def start(self) -> None:
        """Initializes the program, allocates resources."""

    def use(self) -> None:
        """Tells the program that it is used by another consumer.
        Starts the program if this is the first usage."""
        if self.consumers == 0:
            self.start()
        self.consumers += 1

    def stop(self) -> None:
        """Stops the program, releases resources."""

    def release(self) -> None:
        """Tells the program that one consumer does not use it anymore.
        Stops the program if this was the last one."""
        self.consumers -= 1
        if self.consumers == 0:
            self.stop()


class ScreenProgram(VizProgram):
    """The base class for all screen visualization programs."""

    def draw(self) -> None:
        """Called every frame. Updates the screen."""
        raise NotImplementedError()

    def increase_resolution(self) -> None:
        """Called if there is time in the loop to spare.
        Increases the system load, but also increases quality."""

    def decrease_resolution(self) -> None:
        """Called if rendering takes too long.
        Decreases the quality and speeds up the draw call."""


class LedProgram(VizProgram):
    """The base class for all led visualization programs."""

    def compute(self) -> None:
        """Is called once per update. Computation should happen here,
        so they can be reused in the returning functions"""

    def ring_colors(self) -> List[Tuple[float, float, float]]:
        """Returns the colors for the ring, one rgb tuple for each led."""
        raise NotImplementedError()

    def wled_colors(self) -> List[Tuple[float, float, float]]:
        """Returns the colors for WLED, one rgb tuple for each led."""
        raise NotImplementedError()

    def strip_color(self) -> Tuple[float, float, float]:
        """Returns the rgb values for the strip."""
        raise NotImplementedError()


class Disabled(LedProgram, ScreenProgram):
    """A null class to represent inactivity."""

    def __init__(self, lights: "Lights") -> None:
        super().__init__(lights)
        self.name = "Disabled"

    def draw(self) -> None:
        raise NotImplementedError()

    def ring_colors(self) -> List[Tuple[float, float, float]]:
        raise NotImplementedError()

    def wled_colors(self) -> List[Tuple[float, float, float]]:
        raise NotImplementedError()

    def strip_color(self) -> Tuple[float, float, float]:
        raise NotImplementedError()


class Fixed(LedProgram):
    """Show one fixed color only. The color is controlled in the lights module."""

    def __init__(self, lights: "Lights") -> None:
        super().__init__(lights)
        self.name = "Fixed"

    def compute(self) -> None:
        # show a red color if the alarm is active
        alarm_factor = self.lights.alarm_program.factor
        if alarm_factor != -1.0:
            self.lights.fixed_color = (alarm_factor, 0, 0)

    def ring_colors(self) -> List[Tuple[float, float, float]]:
        return [self.lights.fixed_color for _ in range(self.lights.ring.LED_COUNT)]

    def wled_colors(self) -> List[Tuple[float, float, float]]:
        return [self.lights.fixed_color for _ in range(self.lights.wled.led_count)]

    def strip_color(self) -> Tuple[float, float, float]:
        return self.lights.fixed_color


class Rainbow(LedProgram):
    """Continuously cycles through all colors. Affected by the speed setting."""

    def __init__(self, lights: "Lights") -> None:
        super().__init__(lights)
        self.name = "Rainbow"
        self.program_duration = 1
        self.time_passed = 0.0
        self.current_fraction = 0.0

    def start(self) -> None:
        self.time_passed = 0.0

    def compute(self) -> None:
        self.time_passed += self.lights.seconds_per_frame * self.lights.program_speed
        self.time_passed %= self.program_duration
        self.current_fraction = self.time_passed / self.program_duration

    def _colors(self, led_count) -> List[Tuple[float, float, float]]:
        return [
            colorsys.hsv_to_rgb((self.current_fraction + led / led_count) % 1, 1, 1)
            for led in range(led_count)
        ]

    def ring_colors(self) -> List[Tuple[float, float, float]]:
        return self._colors(self.lights.ring.LED_COUNT)

    def wled_colors(self) -> List[Tuple[float, float, float]]:
        return self._colors(self.lights.wled.led_count)

    def strip_color(self) -> Tuple[float, float, float]:
        return colorsys.hsv_to_rgb(self.current_fraction, 1, 1)


class Adaptive(LedProgram):
    """Dynamically reacts to the currently played music.
    Low frequencies are represented by red, high ones by blue."""

    def __init__(self, lights: "Lights") -> None:
        super().__init__(lights)
        self.name = "Rave"
        self.cava = self.lights.cava_program

        # RING
        # map the leds to rainbow colors from red over green to blue
        # (without pink-> hue values in [0, ⅔]
        # stretch the outer regions (red and blue) and compress the inner region (green)
        ring_hues = [
            (2 / 3)
            * 1
            / (
                1
                + math.e
                ** (-4 * math.e * (led / (self.lights.ring.LED_COUNT - 1) - 0.5))
            )
            for led in range(0, self.lights.ring.LED_COUNT)
        ]
        self.ring_base_colors = [colorsys.hsv_to_rgb(hue, 1, 1) for hue in ring_hues]

        # WLED
        # identical to ring, but with a different number of leds
        wled_hues = [
            (2 / 3)
            * 1
            / (
                1
                + math.e
                ** (-4 * math.e * (led / (self.lights.wled.led_count - 1) - 0.5))
            )
            for led in range(0, self.lights.wled.led_count)
        ]
        self.wled_base_colors = [colorsys.hsv_to_rgb(hue, 1, 1) for hue in wled_hues]

        # STRIP
        # distribute frequencies over the three leds. Don't use hard cuts, but smooth functions
        # the functions add up to one at every point and each functions integral is a third
        self.strip_granularity = 16
        self.red_coeffs = [
            -1
            / (
                1
                + math.e ** (-6 * math.e * (led / (self.strip_granularity - 1) - 1 / 3))
            )
            + 1
            for led in range(0, self.strip_granularity)
        ]
        self.blue_coeffs = [
            1
            / (
                1
                + math.e ** (-6 * math.e * (led / (self.strip_granularity - 1) - 2 / 3))
            )
            for led in range(0, self.strip_granularity)
        ]
        self.green_coeffs = [
            1 - self.red_coeffs[led] - self.blue_coeffs[led]
            for led in range(0, self.strip_granularity)
        ]

    def start(self) -> None:
        self.cava.use()

    def compute(self) -> None:
        pass

    def _aggregate_frame(self, led_count) -> List[float]:
        # aggregate the length of cavas frame into a list the length of the number of leds we have.
        # This reduces computation time.
        values_per_led = len(self.cava.current_frame) // led_count
        left = len(self.cava.current_frame) - values_per_led * led_count

        start = 0

        aggregated = []
        for led in range(led_count):
            end = start + values_per_led
            bin_size = values_per_led
            if left > 0:
                end += 1
                left -= 1
                bin_size += 1

            aggregated.append(sum(self.cava.current_frame[start:end]) / bin_size)
            start += values_per_led
        return aggregated

    def ring_colors(self) -> List[Tuple[float, float, float]]:
        aggregated = self._aggregate_frame(self.lights.ring.LED_COUNT)
        colors = [
            tuple(factor * val for val in color)
            for factor, color in zip(aggregated, self.ring_base_colors)
        ]
        # https://github.com/python/mypy/issues/5068
        return cast(List[Tuple[float, float, float]], colors)

    def wled_colors(self) -> List[Tuple[float, float, float]]:
        aggregated = self._aggregate_frame(self.lights.wled.led_count)
        colors = [
            tuple(factor * val for val in color)
            for factor, color in zip(aggregated, self.wled_base_colors)
        ]
        # https://github.com/python/mypy/issues/5068
        return cast(List[Tuple[float, float, float]], colors)

    def strip_color(self) -> Tuple[float, float, float]:
        aggregated = self._aggregate_frame(self.strip_granularity)
        red = (
            sum(coeff * val for coeff, val in zip(self.red_coeffs, aggregated))
            * 3
            / self.strip_granularity
        )
        green = (
            sum(coeff * val for coeff, val in zip(self.green_coeffs, aggregated))
            * 3
            / self.strip_granularity
        )
        blue = (
            sum(coeff * val for coeff, val in zip(self.blue_coeffs, aggregated))
            * 3
            / self.strip_granularity
        )
        red = min(1.0, red)
        green = min(1.0, green)
        blue = min(1.0, blue)
        return red, green, blue

    def stop(self) -> None:
        self.cava.release()


class Alarm(VizProgram):
    """This program makes the leds flash red in sync to the played sound.
    Only computes the brightness, does not display it."""

    def __init__(self, lights: "Lights") -> None:
        super().__init__(lights)
        self.name = "Alarm"
        self.time_passed = 0.0
        self.sound_count = 0
        self.increasing_duration = 0.45
        self.decreasing_duration = 0.8
        self.sound_duration = 2.1
        self.sound_repetition = 2.5
        self.factor = -1.0

    def start(self) -> None:
        self.time_passed = 0.0
        self.sound_count = 0
        self.factor = 0

    def compute(self) -> None:
        """If active, compute the brightness for the red color,
        depending on the time that has passed since starting the sound."""
        # do not compute if the alarm is not active
        if self.consumers == 0:
            return
        self.time_passed += self.lights.seconds_per_frame
        if self.time_passed >= self.sound_repetition:
            self.sound_count += 1
            self.time_passed %= self.sound_repetition

        if self.sound_count >= 4:
            self.factor = 0
            return
        if self.time_passed < self.increasing_duration:
            self.factor = self.time_passed / self.increasing_duration
        elif self.time_passed < self.sound_duration - self.decreasing_duration:
            self.factor = 1
        elif self.time_passed < self.sound_duration:
            self.factor = (
                1
                - (self.time_passed - (self.sound_duration - self.decreasing_duration))
                / self.decreasing_duration
            )
        else:
            self.factor = 0

    def stop(self) -> None:
        self.factor = -1.0


class Cava(VizProgram):
    """This Program manages the interaction with cava.
    It provides the current frequencies for other programs to use."""

    def __init__(self, lights: "Lights") -> None:
        super().__init__(lights)

        self.cava_fifo_path = os.path.join(settings.BASE_DIR, "config/cava_fifo")

        # Keep these configurations in sync with config/cava.config
        self.bars = 199
        self.bit_format = 8

        self.frame_length = self.bars * (self.bit_format // 8)

        self.current_frame: List[float] = []
        self.growing_frame = b""
        self.cava_process: Optional[subprocess.Popen[bytes]] = None
        self.cava_fifo = -1

    def start(self) -> None:
        self.current_frame = [0 for _ in range(self.bars)]
        self.growing_frame = b""
        try:
            # delete old contents of the pipe
            os.remove(self.cava_fifo_path)
        except FileNotFoundError:
            # the file does not exist
            pass
        try:
            os.mkfifo(self.cava_fifo_path)
        except FileExistsError:
            # the file already exists
            logging.info("%s already exists while starting", self.cava_fifo_path)

        self.cava_process = subprocess.Popen(
            ["cava", "-p", os.path.join(settings.BASE_DIR, "config/cava.config")],
            cwd=settings.BASE_DIR,
        )
        # cava_fifo = open(cava_fifo_path, 'r')
        self.cava_fifo = os.open(self.cava_fifo_path, os.O_RDONLY | os.O_NONBLOCK)

    def compute(self) -> None:
        """If active, read output from the cava program.
        Make sure that the most recent frame is always fully available,
        Stores incomplete frames for the next update."""
        # do not compute if no program uses cava
        if self.consumers == 0:
            return
        # read the fifo until we get to the current frame
        while True:
            try:
                read = os.read(
                    self.cava_fifo, self.frame_length - len(self.growing_frame)
                )
                if read == b"":
                    return
                self.growing_frame += read
            except OSError as e:
                if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                    # there were not enough bytes for a whole frame, keep the old frame
                    return

            # we read a whole frame, update the factors
            if len(self.growing_frame) == self.frame_length:
                # vol = max(0.01, self.lights.base.musiq.player.volume)
                # self.current_frame = [int(b) / 255 / vol for b in self.growing_frame]
                self.current_frame = [int(b) / 255 for b in self.growing_frame]
                self.growing_frame = b""

    def stop(self) -> None:
        try:
            os.close(self.cava_fifo)
        except OSError as e:
            logging.info("fifo already closed: %s", e)
        except TypeError as e:
            logging.info("fifo does not exist: %s", e)

        if self.cava_process:
            self.cava_process.terminate()

        try:
            os.remove(self.cava_fifo_path)
        except FileNotFoundError as e:
            # the file was already deleted
            logging.info("%s not found while deleting: %s", self.cava_fifo_path, e)
