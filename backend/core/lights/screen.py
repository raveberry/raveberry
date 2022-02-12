"""This module handles the screen configuration."""
import math
import re
import subprocess
import os
from typing import List, Tuple, cast

from django.conf import settings as conf
from core import redis, util
from core.lights import lights
from core.lights.device import Device
from core.settings import storage


class Screen(Device):
    """This class provides an interface to control the screen."""

    @staticmethod
    def get_primary() -> str:
        """Return the primary screen"""
        for line in subprocess.check_output(
            "xrandr -q".split(), text=True
        ).splitlines():
            output = re.match(r"(\S+) connected primary", line)
            if output:
                return output.group(1)
        raise ValueError("Could not find primary screen")

    def __init__(self, manager) -> None:
        super().__init__(manager, "screen")

        # set the DISPLAY environment variable the correct X Display is used
        os.environ["DISPLAY"] = ":0"
        # the visualization needs X to work, so we check if it is running
        try:
            subprocess.check_call(
                "xset q".split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            # Cannot connect to X
            return

        # disable blanking and power saving
        subprocess.call("xset s off".split())
        subprocess.call("xset s noblank".split())
        subprocess.call("xset -dpms".split())

        # ignore the scale factor for large displays,
        # we always render fullscreen without scaling
        os.environ["WINIT_X11_SCALE_FACTOR"] = "1"

        # method should additionally check whether hdmi is connected
        # however, I found no way to do that
        # without hdmi_force_hotplug=1:
        # tvservice -M gives attached events, but tvserice -s is always connected
        # hdmi cannot be plugged in after boot
        # with hdmi_force_hotplug=1:
        # tvservice -M records nothing, tvserice -s is always connected
        # /sys/class/drm/card1-HDMI-A-1/status is always connected
        #
        # so we set hotplug and initialize the screen even if none is connected
        self.initialized = True
        redis.put("screen_initialized", True)

        self.output = self.get_primary()
        self.resolution = (0, 0)  # set in adjust
        self.adjust()

    def adjust(self) -> None:
        """Updates resolutions and resets the current one.
        Needed after changing screens or hotplugging after booting without a connected screen."""
        self.resolution = storage.get("initial_resolution")
        resolutions = list(reversed(sorted(self.list_resolutions())))
        redis.put("resolutions", resolutions)
        # if unset, initialize with the highest resolution
        if self.resolution == (0, 0):
            storage.put("initial_resolution", resolutions[0])
            self.resolution = resolutions[0]
        self.set_resolution(self.resolution)

    def clear(self) -> None:
        # when no program is running, nothing is shown on screen
        pass

    def list_resolutions(self) -> List[Tuple[int, int]]:
        """Returns all supported resolutions that match the preferred resolution in aspect ratio."""
        if not self.initialized:
            return []
        modes = []
        listing_modes = False
        preferred_mode = (1280, 720)
        for line in subprocess.check_output(
            "xrandr -q".split(), text=True
        ).splitlines():
            output = re.match(r"(\S+) connected", line)
            if output:
                listing_modes = output.group(1) == self.output
            if not listing_modes:
                continue
            match = re.match(r"\s+(\d+x\d+)\s+\d+\.\d+", line)
            if match:
                mode = tuple(map(int, match.group(1).split("x")))
                mode = cast(Tuple[int, int], mode)
                modes.append(mode)
                if "+" in line:
                    preferred_mode = mode
        preferred_ratio = preferred_mode[0] / preferred_mode[1]
        usable_modes = []
        for mode in modes:
            ratio = mode[0] / mode[1]
            if math.isclose(ratio, preferred_ratio, rel_tol=0.1):
                usable_modes.append(mode)
        return usable_modes

    def set_resolution(self, resolution: Tuple[int, int]) -> None:
        """Sets the current output to the given resolution.
        Also updates the background in production."""
        if not self.initialized:
            return
        subprocess.call(
            [
                "xrandr",
                "--output",
                self.output,
                "--mode",
                util.format_resolution(resolution),
            ]
        )

        if not conf.DEBUG:
            # show a background that is visible when the visualization is not rendering
            # needs to be reset every resolution change
            try:
                subprocess.call(
                    [
                        "feh",
                        "--bg-max",
                        os.path.join(conf.BASE_DIR, "resources/images/background.png"),
                    ]
                )
            except FileNotFoundError:
                pass

        redis.put("current_resolution", resolution)
        self.resolution = resolution
        lights.update_state()

    def lower_resolution(self) -> None:
        """Sets the resolution to the next resolution with similar ratio that is smaller."""
        if not self.initialized:
            return
        resolutions = redis.get("resolutions")
        index = resolutions.index(self.resolution)
        index = min(index + 1, len(resolutions) - 1)
        self.set_resolution(resolutions[index])
