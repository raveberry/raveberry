from django.conf import settings

import os
import math
import errno
import colorsys
import subprocess

class VizProgram:

    def __init__(self, lights):
        self.lights = lights
        self.consumers = 0

    def start(self):
        ''' initializes the program, allocates resources '''
        pass

    def use(self):
        ''' tells the program that it is used by another consumer
        starts the program if this was the first one '''
        if self.consumers == 0:
            self.start()
        self.consumers += 1

    def compute(self):
        ''' is called once per led frame. computation should happen here, 
        results are only returned in color functions'''
        pass

    def stop(self):
        ''' stops the program, releases resources '''
        pass

    def release(self):
        ''' tells the program that one consumer does not use it anymore
        stops the program if this was the last one '''
        self.consumers -= 1
        if self.consumers == 0:
            self.stop()

class Disabled(VizProgram):

    def __init__(self, lights):
        super().__init__(lights)
        self.name = 'Disabled'

    def ring_colors(self):
        print('requested disabled ring_colors!')

    def strip_color(self):
        print('requested disabled strip_color!')

    def draw(self):
        print('requested disabled draw!')

    def increase_resolution(self):
        pass

    def decrease_resolution(self):
        pass

class Fixed(VizProgram):

    def __init__(self, lights):
        super().__init__(lights)
        self.name = 'Fixed'
        self.color = (0, 0, 0)

    def compute(self):
        # show a red color if the alarm is active
        alarm_factor = self.lights.alarm_program.factor
        if alarm_factor != -1:
            self.color = (alarm_factor, 0, 0)

    def ring_colors(self):
        return [self.color for led in range(self.lights.ring.LED_COUNT)]

    def strip_color(self):
        return self.color

class Rainbow(VizProgram):

    def __init__(self, lights):
        super().__init__(lights)
        self.name = 'Rainbow'
        self.program_duration = 1

    def start(self):
        self.time_passed = 0

    def compute(self):
        self.time_passed += self.lights.seconds_per_frame * self.lights.program_speed
        self.time_passed %= self.program_duration
        self.current_fraction = self.time_passed / self.program_duration

    def ring_colors(self):
        return [colorsys.hsv_to_rgb((self.current_fraction + led / self.lights.ring.LED_COUNT) % 1, 1, 1) \
            for led in range(self.lights.ring.LED_COUNT)]

    def strip_color(self):
        return colorsys.hsv_to_rgb(self.current_fraction, 1, 1);

class Adaptive(VizProgram):

    def __init__(self, lights):
        super().__init__(lights)
        self.name = 'Rave'
        self.cava = self.lights.cava_program

        # RING
        # map the leds to rainbow colors from red over green to blue (without pink-> hue values in [0, ⅔]
        # stretch the outer regions (red and blue) and compress the inner region (green)
        self.led_count = self.lights.ring.LED_COUNT
        hues = [2/3 * 1 / (1 + math.e**(-4*math.e*(led/(self.led_count-1)-0.5))) for led in range(0, self.led_count)]
        self.base_colors = [colorsys.hsv_to_rgb(hue, 1, 1) for hue in hues]

        # STRIP
        # distribute frequencies over the three leds. Don't use hard cuts, but smooth functions
        # the functions add up to one at every point and each functions integral is a third
        self.red_coeffs = [-1 / (1 + math.e**(-6*math.e*(led/(self.led_count-1)-1/3))) + 1 for led in range(0, self.led_count)]
        self.blue_coeffs = [1 / (1 + math.e**(-6*math.e*(led/(self.led_count-1)-2/3))) for led in range(0, self.led_count)]
        self.green_coeffs = [1 - self.red_coeffs[led] - self.blue_coeffs[led] for led in range(0, self.led_count)]

    def start(self):
        self.cava.use()

    def compute(self):
        # aggregate the length of cavas frame into a list the length of the number of leds we have. This reduces computation
        values_per_led = len(self.cava.current_frame) // self.led_count
        self.current_frame = []
        for led in range(self.led_count):
            self.current_frame.append(sum(self.cava.current_frame[led*values_per_led:(led+1)*values_per_led]) / values_per_led)
    
    def ring_colors(self):
        return [tuple(factor * val for val in color) for factor, color in zip(self.current_frame, self.base_colors)]

    def strip_color(self):
        red = sum(coeff * val for coeff, val in zip(self.red_coeffs, self.current_frame)) * 3 / self.led_count
        green = sum(coeff * val for coeff, val in zip(self.green_coeffs, self.current_frame)) * 3 / self.led_count
        blue = sum(coeff * val for coeff, val in zip(self.blue_coeffs, self.current_frame)) * 3 / self.led_count
        red = min(1, red)
        green = min(1, green)
        blue = min(1, blue)
        return (red, green, blue)
    
    def stop(self):
        self.cava.release()

class Alarm(VizProgram):

    def __init__(self, lights):
        super().__init__(lights)
        self.name = 'Alarm'
        self.time_passed = 0
        self.sound_count = 0
        self.increasing_duration = 0.45
        self.decreasing_duration = 0.8
        self.sound_duration = 2.1
        self.sound_repetition = 2.5
        self.factor = -1

    def start(self):
        self.time_passed = 0
        self.sound_count = 0
        self.factor = 0

    def compute(self):
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
            self.factor = 1 - (self.time_passed - (self.sound_duration - self.decreasing_duration)) / self.decreasing_duration
        else:
            self.factor = 0

    def stop(self):
        self.factor = -1

class Cava(VizProgram):
    def __init__(self, lights):
        super().__init__(lights)

        self.cava_fifo_path = os.path.join(settings.BASE_DIR, 'config/cava_fifo')

        # Keep these configurations in sync with config/cava.config
        self.bars = 199
        self.bit_format = 8

        self.frame_length = self.bars * (self.bit_format // 8)
    
    def start(self):
        self.current_frame = [0 for led in range(self.bars)]
        self.growing_frame = b''
        try:
            # delete old contents of the pipe
            os.remove(self.cava_fifo_path)
        except FileNotFoundError as e:
            # the file does not exist
            pass
        try:
            os.mkfifo(self.cava_fifo_path)
        except FileExistsError as e:
            # the file already exists
            print(self.cava_fifo_path + ' already exists while starting')

        self.cava_process = subprocess.Popen(['cava', '-p', os.path.join(settings.BASE_DIR, 'config/cava.config')], cwd=settings.BASE_DIR)
        #cava_fifo = open(cava_fifo_path, 'r')
        self.cava_fifo = os.open(self.cava_fifo_path, os.O_RDONLY | os.O_NONBLOCK) 

    def compute(self):
        # do not compute if no program uses cava
        if self.consumers == 0:
            return
        # read the fifo until we get to the current frame
        while True:
            try:
                read = os.read(self.cava_fifo, self.frame_length - len(self.growing_frame))
                if read == b'':
                    return
                self.growing_frame += read
            except OSError as e:
                if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                    # there were not enough bytes for a whole frame, keep the old frame
                    return
                else:
                    raise

            # we read a whole frame, update the factors
            if len(self.growing_frame) == self.frame_length:
                #vol = max(0.01, self.lights.base.musiq.player.volume)
                #self.current_frame = [int(b) / 255 / vol for b in self.growing_frame]
                self.current_frame = [int(b) / 255 for b in self.growing_frame]
                self.growing_frame = b''

    def stop(self):
        try:
            os.close(self.cava_fifo)
        except OSError as e:
            print('cava fifo already closed: ' + str(e))
        except TypeError as e:
            print('cava fifo does not exist: ' + str(e))

        self.cava_process.terminate()

        try:
            os.remove(self.cava_fifo_path)
        except FileNotFoundError as e:
            # the file was already deleted
            print(self.cava_fifo_path + ' not found while deleting: ' + str(e))
