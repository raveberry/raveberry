"""This module handles the screen configuration."""

import importlib.util
import subprocess
import time
import os

from core.lights.device import Device


class Screen(Device):
    """This class provides an interface to control the screen."""

    def __init__(self, lights) -> None:
        super().__init__(lights, "screen")
        self.initialized = False
        self.adjust()

    def adjust(self) -> None:
        """Check whether the system is set up to run screen visualization.
        Resets the resolution, needed after hotplugging Raspberry Pis for higher resolution."""

        # require pi3d to be installed
        spec = importlib.util.find_spec("pi3d")
        if spec is None:
            return

        # pi3d needs X to work, so we check if it is running
        # set the DISPLAY environment variable so pi3d uses the correct X Display
        os.environ["DISPLAY"] = ":0"

        # don't offer this feature on raspberry pi 3
        try:
            with open("/proc/device-tree/model") as f:
                model = f.read()
                if model.startswith("Raspberry Pi 3"):
                    return
                if model.startswith("Raspberry Pi 4"):
                    # restart X to increase resolution if the cable was plugged in after boot
                    subprocess.call(["sudo", "/usr/local/sbin/raveberry/restart_x"])

                    for _ in range(20):
                        try:
                            subprocess.check_call(
                                "xset q".split(),
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            break
                        except subprocess.CalledProcessError:
                            time.sleep(0.1)
                    else:
                        # X could not be started for some reason
                        return
        except FileNotFoundError:
            # we are not running on a raspberry pi
            try:
                subprocess.check_call(
                    "xset q".split(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                # Cannot connect to X
                return

        # this method should additionally check whether hdmi is connected
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

    def clear(self):
        pass
