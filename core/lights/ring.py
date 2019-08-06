import rpi_ws281x 

class Ring:

    def __init__(self):
        # LED ring configuration:
        LED_COUNT      = 16      # Number of LED pixels.
        LED_PIN        = 10      # GPIO pin connected to the pixels (10: SPI, 18: PWM (used for sound).
        LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
        LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
        LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
        LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
        LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

        self.LED_COUNT = LED_COUNT
        self.LED_OFFSET = 12
        self.brightness = 1
        self.monochrome = False

        self.controller = rpi_ws281x.Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL) 
        try:
            self.controller.begin()
            self.initialized = True
        except RuntimeError:
            # could not connect to led ring
            self.initialized = False

    def set_colors(self, colors):
        if not self.initialized:
            return
        for led in range(self.LED_COUNT):
            dimmed_color = (self.brightness * val for val in colors[led])
            scaled_color = tuple(int(val * 255) for val in dimmed_color)
            self.controller.setPixelColorRGB((led + self.LED_OFFSET) % self.LED_COUNT, *scaled_color)
        self.controller.show()

    def clear(self):
        if not self.initialized:
            return
        for led in range(self.LED_COUNT):
            self.controller.setPixelColorRGB(led, 0, 0, 0)
        self.controller.show()
