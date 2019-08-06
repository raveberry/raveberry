import Adafruit_PCA9685

class Strip:

    def __init__(self):
        try:
            self.controller = Adafruit_PCA9685.PCA9685()
            self.initialized = True
        except (RuntimeError, OSError):
            # LED strip is not connected
            self.initialized = False

        self.brightness = 1

    def set_color(self, color):
        if not self.initialized:
            return

        for channel, val in enumerate(color):
            # map the value to the interval [0, 4095]
            dimmed_val = val * self.brightness
            scaled_val = round(dimmed_val * 4095)
            self.controller.set_pwm(channel, 0, scaled_val)

    def clear(self):
        if not self.initialized:
            return

        for channel in range(3):
            self.controller.set_pwm(channel, 0, 0)
