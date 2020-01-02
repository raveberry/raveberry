import importlib

class Screen:

    def __init__(self):
        self.initialized = False
        self.adjust()

    def adjust(self):
        # only allow this feature on raspberry pi 4
        try:
            with open('/proc/device-tree/model') as f:
                model = f.read()
                if not model.startswith('Raspberry Pi 4'):
                    return
        except FileNotFoundError:
            return
        # require pi3d to be installed
        spec = importlib.util.find_spec("pi3d")
        if spec is None:
            return
        # this method should check whether hdmi is connected and set the value accordingly
        # however, I found no method to do that
        # without hdmi_force_hotplug=1:
        # tvservice -M gives attached events, but tvserice -s is always connected
        # hdmi cannot be plugged in after boot
        # with hdmi_force_hotplug=1:
        # tvservice -M records nothing, tvserice -s is always connected
        # /sys/class/drm/card1-HDMI-A-1/status is always connected
        #
        # so we set hotplug and alway initialize the screen even if none is connected
        self.initialized = True
