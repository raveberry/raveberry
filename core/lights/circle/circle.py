from django.conf import settings

from core.lights.programs import VizProgram

import os
import sys
import time
import math
import random
import ctypes
import subprocess

class Circle(VizProgram):

    def __init__(self, lights):
        super().__init__(lights)
        self.name = 'Circular'
        self.cava = lights.cava_program

        # To have pi3d display shader compilation errors, set the logging level to INFO
        #import logging
        #logging.basicConfig(level=logging.INFO)

        # The appearance of the shader was taken from
        # https://www.shadertoy.com/view/llycWD

        # The width and height of the displayed visualizer in pixels
        self.WIDTH = 640
        self.HEIGHT = 480
        # this scale value determines how many times bigger the actual display is in comparison to the actually computed buffer. Higher values equal lower computation but also lower resolution.
        self.SCALE = 1

        # The number of ffts that are kept in history
        self.FFT_HIST = 8
        # The part of the spectrum that is used to detect loud bass, making the circle bigger
        self.BASS_MAX = 0.05
        # The size of the sliding window we use for smoothing of the spectrum
        self.SMOOTH_RANGE = 5
        # The amount of particles (without mirroring)
        # when changing this value, change it in particle.vs as well
        self.NUM_PARTICLES = 200
        # Size of the particles
        self.PARTICLE_SIZE = 0.01
        # How far away to spawn particles
        self.PARTICLE_SPAWN_Z = 2.0
        # How much impact the bass has on the particles
        self.BASS_IMPACT_ON_PARTICLES = 1.0

        self.should_prepare = False
        self.should_resize = False

        # https://stackoverflow.com/questions/48472285/create-core-context-with-glut-freeglut
        # In order to use newer OpenGL versions (e.g. for Instancing), use the following line:
        # glutInitContextVersion( 3, 3 );

    def set_resolution(self, width, height):
        self.WIDTH, self.HEIGHT = width, height
        # HD works alright, use it to compute a starting SCALE (multiples of 0.5)
        self.SCALE = round(width * height / (1280 * 720) * 2) / 2
        self.SCALE = max(self.SCALE, 1)

    def start(self):
        self.cava.use()

        # pi3d on the raspberry pi 4 needs X to work, so we start a server here.
        # have it sleep indefinitely so it doesn't immediately stop
        self.x11 = subprocess.Popen('xinit /bin/sleep infinity -- :0'.split(), universal_newlines=True, stderr=subprocess.PIPE)
        # wait until X is initialized
        while True:
            line = self.x11.stderr.readline()
            if 'Initializing kms color map' in line:
                break
        # set the DISPLAY environment variable so pi3d uses the correct X Display
        os.environ['DISPLAY'] = ':0'

        # now read the resolution from the X window and set our dimensions accordingly. Uses the DISPLAY environ variable
        # alternative without X would be tvserice -d edid.dat && edidparser edid.dat
        xwininfo = subprocess.check_output('xwininfo -root'.split()).decode().splitlines()
        width, height = 640, 480
        for line in xwininfo:
            line = line.strip()
            if line.startswith('Width:'):
                width = int(line.split()[1])
            if line.startswith('Height:'):
                height = int(line.split()[1])
        self.set_resolution(width, height)

        self.resolution_increases = {}

        self.should_prepare = True

        self.update_active_fft = True

    def increase_resolution(self):
        if self.SCALE == 1:
            # do not render more than one pixel per pixel
            return

        # if we get told to increase at a specific resolution a lot of times, we got probably caught in an oscillation. Don't increase resolution then
        scale_key = round(self.SCALE, 1)
        if scale_key not in self.resolution_increases:
            self.resolution_increases[scale_key] = 0
        if self.resolution_increases[scale_key] >= 2:
            return
        self.resolution_increases[scale_key] += 1

        self.SCALE = max(1, self.SCALE - 0.5)
        self.should_resize = True

    def decrease_resolution(self):
        self.SCALE = self.SCALE + 0.5
        self.should_resize = True
    
    def _prepare(self):
        self.should_prepare = False

        import numpy as np
        # pi3d has to be imported in the same thread that it will draw in
        # Thus, import it here instead of at the top of the file
        import pi3d
        from pi3d.constants import GL_CLAMP_TO_EDGE
        
        # Setup display and initialise pi3d
        self.display = pi3d.Display.create(w=self.WIDTH, h=self.HEIGHT, window_title="OpenGL")
        # Set a pink background color so mistakes are clearly visible
        #self.display.set_background(1, 0, 1, 1)
        self.display.set_background(0, 0, 0, 1)

        '''
        Visualization is split into five parts:
        The background, the particles, the spectrum, the logo and after effects.
        * The background is a vertical gradient that cycles through HSV color space, speeding up with strong bass.
        * Particles are multiple sprites that are created at a specified x,y-coordinate and fly towards the camera.
          Due to the projection into screenspace they seem to move away from the center.
        * The spectrum is a white circle that represents the fft-transformation of the currently played audio. It is smoothed to avoid strong spikes.
        * The logo is a black circle on top of the spectrum containing the logo.
        * After effects add a vignette.
        Each of these parts is represented with pi3d Shapes. They have their own shader and are ordered on the z-axis to ensure correct overlapping.
        '''

        background_shader = pi3d.Shader(os.path.join(settings.BASE_DIR, 'core/lights/circle/background'))
        self.background = pi3d.Sprite(w=2, h=2)
        self.background.set_shader(background_shader)
        self.background.positionZ(0.9)

        self.particle_shader = pi3d.Shader(os.path.join(settings.BASE_DIR, 'core/lights/circle/particle'))
        # create one sprite for all particles and an array containing the position and speed for all of them
        self.particle_sprite = pi3d.Sprite(w=self.PARTICLE_SIZE, h=self.PARTICLE_SIZE)
        self.particle_sprite.set_shader(self.particle_shader)
        self.particle_sprite.positionZ(0)
        self.particles = np.zeros((self.NUM_PARTICLES, 4), dtype='float32')

        spectrum_shader = pi3d.Shader(os.path.join(settings.BASE_DIR, 'core/lights/circle/spectrum'))
        self.spectrum = pi3d.Sprite(w=2, h=2)
        self.spectrum.set_shader(spectrum_shader)
        self.spectrum.positionZ(-0.9)

        logo_shader = pi3d.Shader(os.path.join(settings.BASE_DIR, 'core/lights/circle/logo'))
        self.logo = pi3d.Sprite(w=2, h=2)
        self.logo.set_shader(logo_shader)
        self.logo.positionZ(-0.95)
        logo_texture = pi3d.Texture(os.path.join(settings.BASE_DIR, 'static/graphics/raveberry_square.png'))
        self.logo.set_textures([logo_texture])

        after_shader = pi3d.Shader(os.path.join(settings.BASE_DIR, 'core/lights/circle/after'))
        self.after = pi3d.Sprite(w=2, h=2)
        self.after.set_shader(after_shader)
        self.after.positionZ(-1.)

        # initialize the spectogram history with zeroes
        self.fft_active = np.zeros((self.FFT_HIST // 2, self.cava.bars - self.SMOOTH_RANGE, 4), dtype=np.uint8)
        self.fft_inactive = np.zeros((self.FFT_HIST // 2, self.cava.bars - self.SMOOTH_RANGE, 4), dtype=np.uint8)

        self.spectrum_texture = pi3d.Texture(self.fft_active.copy())
        # Prevent interpolation from opposite edge
        self.spectrum_texture.m_repeat = GL_CLAMP_TO_EDGE
        self.spectrum.set_textures([self.spectrum_texture])

        # create an OffscreenTexture to allow scaling. By first rendering into a smaller Texture a lot of computation is saved. This OffscreenTexture is then drawn at the end of the draw loop.
        # do not use a new perspective camera with the new scale to have the particles behave identically regardless of scale
        self.post = pi3d.PostProcess(os.path.join(settings.BASE_DIR, 'core/lights/circle/scale'), scale=1/self.SCALE)

        self.total_bass = 0
        self.last_loop = time.time()
        self.time_elapsed = 0

        shader = pi3d.Shader("uv_flat")

        self.counter = 0

    def draw(self):
        import numpy as np
        import pi3d
        from pi3d.constants import opengles, GL_LESS, GL_ALWAYS, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA
        # used for reimplementing the draw call with instancing
        from pi3d.constants import GLsizei, GLint, GLboolean, GL_FLOAT, GL_UNSIGNED_SHORT

        time_logging = False

        if self.should_prepare:
            self._prepare()

        if self.should_resize:
            self.should_resize = False
            self.post = pi3d.PostProcess(os.path.join(settings.BASE_DIR, 'core/lights/circle/scale'), scale=1/self.SCALE)

        if self.lights.alarm_program.factor != -1:
            alarm_factor = max(0.001, self.lights.alarm_program.factor)
        else:
            alarm_factor = 0

        self.display.loop_running()
        now = self.display.time
        time_delta = now - self.last_loop
        self.last_loop = now
        self.time_elapsed += time_delta

        then = time.time()

        # use a sliding window to smooth the spectrum with a gauss function
        current_frame = np.array(self.cava.current_frame)
        new_frame = np.zeros(self.cava.bars - self.SMOOTH_RANGE)
        bin_size = self.SMOOTH_RANGE
        def gauss(x,sigma=1):
            return 1 / (sigma * np.sqrt(2 * np.pi)) * np.exp(-(x)**2/(2*sigma**2))
        factors = gauss(np.linspace(-1, 1, bin_size))
        for i in range(len(current_frame) - bin_size):
            s = 0
            for j in range(bin_size):
                s += factors[j] * current_frame[i+j]
            new_frame[i] = s
            # somehow this is slower that the code above
            #new_frame[i] = np.sum(factors * current_frame[i:i+bin_size])

        # have the value grow steeper in the beginning, but end smoothly on 1
        new_frame = new_frame / np.sum(factors)
        new_frame = -0.5*new_frame**3+1.5*new_frame
        new_frame *= 255
        current_frame = new_frame

        if time_logging:
            print(f'{time.time() - then} spectrum smoothing')
            then = time.time()

        # Value used for circle shake and background color cycle
        # select the first few values and compute their average
        bass_elements = math.ceil(self.BASS_MAX * self.cava.bars)
        bass_value = sum(current_frame[0:bass_elements]) / bass_elements / 255
        bass_value = max(bass_value, alarm_factor)
        self.total_bass = self.total_bass + bass_value

        # start rendering to the smaller OffscreenTexture
        self.post.start_capture()

        self.background.unif[48] = self.WIDTH
        self.background.unif[49] = self.HEIGHT
        self.background.unif[50] = self.SCALE
        self.background.unif[54] = self.time_elapsed
        self.background.unif[56] = alarm_factor
        self.background.unif[58] = self.total_bass
        self.background.draw()

        if time_logging:
            print(f'{time.time() - then} background draw')
            then = time.time()

        self._advance_particles(bass_value)

        if time_logging:
            print(f'{time.time() - then} particle advance')
            then = time.time()

        # enable additive blending so the draw order of overlapping particles does not matter
        opengles.glBlendFunc(1, 1)
        opengles.glDepthFunc(GL_ALWAYS)

        self.particle_sprite.unif[50] = self.SCALE
        self.particle_sprite.unif[53] = self.PARTICLE_SPAWN_Z
        self.particle_sprite.unif[54] = self.time_elapsed

        # we don't need to handle the shape, we can directly draw the buffer
        # simplified version of Buffer.draw()
        # we don't need modelmatrices, normals ord textures and always blend
        buf = self.particle_sprite.buf[0]
        buf.load_opengl()
        shader = buf.shader
        shader.use()
        opengles.glUniform3fv(shader.unif_unif, GLsizei(20), self.particle_sprite.unif)
        buf._select()
        opengles.glVertexAttribPointer(shader.attr_vertex, GLint(3), GL_FLOAT, GLboolean(0), buf.N_BYTES, 0)
        opengles.glEnableVertexAttribArray(shader.attr_vertex)
        opengles.glVertexAttribPointer(shader.attr_texcoord, GLint(2), GL_FLOAT, GLboolean(0), buf.N_BYTES, 24)
        opengles.glEnableVertexAttribArray(shader.attr_texcoord)
        buf.disp.last_shader = shader
        opengles.glUniform3fv(shader.unif_unib, GLsizei(5), buf.unib)

        position = self.particles.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        position = (ctypes.c_float * (self.particles.shape[0] * 4))(*self.particles.flat)
        opengles.glUniform4fv(opengles.glGetUniformLocation(shader.program, b"positions"), GLsizei(self.NUM_PARTICLES), position)

        opengles.glDrawElementsInstanced(buf.draw_method, GLsizei(buf.ntris * 3), GL_UNSIGNED_SHORT, 0, self.NUM_PARTICLES)

        # restore normal blending
        opengles.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        opengles.glDepthFunc(GL_LESS)

        if time_logging:
            print(f'{time.time() - then} particle draw')
            then = time.time()

        # roll the history one further, insert the current one. 
        # Only do this every second frame to have a longer past
        current_frame = np.array([[val, 0, 0, 0] for val in current_frame], dtype=np.uint8)
        if self.update_active_fft:
            self.update_active_fft= False
            self.fft_active = np.roll(self.fft_active, 1, 0)
            self.fft_active[0] = current_frame
            self.spectrum_texture.update_ndarray(self.fft_active, 0)
        else:
            self.update_active_fft = True
            self.fft_inactive = np.roll(self.fft_inactive, 1, 0)
            self.fft_inactive[0] = current_frame
            self.spectrum_texture.update_ndarray(self.fft_inactive, 0)

        if time_logging:
            print(f'{time.time() - then} spectrum roll')
            then = time.time()

        self.spectrum.unif[48] = self.WIDTH
        self.spectrum.unif[49] = self.HEIGHT
        self.spectrum.unif[50] = self.SCALE
        self.spectrum.unif[51] = self.FFT_HIST
        self.spectrum.unif[52] = self.NUM_PARTICLES
        self.spectrum.unif[53] = self.PARTICLE_SPAWN_Z
        self.spectrum.unif[54] = self.time_elapsed
        self.spectrum.unif[55] = time_delta
        self.spectrum.unif[57] = bass_value
        self.spectrum.unif[58] = self.total_bass
        self.spectrum.draw()

        if time_logging:
            print(f'{time.time() - then} spectrum draw')
            then = time.time()

        self.logo.unif[48] = self.WIDTH
        self.logo.unif[49] = self.HEIGHT
        self.logo.unif[50] = self.SCALE
        self.logo.unif[54] = self.time_elapsed
        self.logo.unif[57] = bass_value
        self.logo.unif[58] = self.total_bass
        self.logo.draw()

        if time_logging:
            print(f'{time.time() - then} logo draw')
            then = time.time()

        self.after.unif[48] = self.WIDTH
        self.after.unif[49] = self.HEIGHT
        self.after.unif[50] = self.SCALE
        self.after.unif[54] = self.time_elapsed
        self.after.unif[57] = bass_value
        self.after.draw()

        if time_logging:
            print(f'{time.time() - then} after draw')
            then = time.time()

        self.post.end_capture()

        self.post.sprite.unif[50] = self.SCALE
        self.post.draw()

        if time_logging:
            print(f'{time.time() - then} post draw')
            then = time.time()
            print('=====')

    def _advance_particles(self, bass):
        ''' moves all particles depending on the given bass value '''
        for index in range(self.particles.shape[0]):
            z = self.particles[index,2]
            speed = self.particles[index,3]

            z -= 0.02 * (speed + bass*self.BASS_IMPACT_ON_PARTICLES);
            self.particles[index,2] = z
            
            # Out of screen, load new particle
            if z <= 0:
                # Generate random particle
                phi = random.random() * 2 * math.pi
                radius_diff = random.random()
                x = math.cos(phi) * (0.2 + radius_diff * 0.05)
                y = math.sin(phi) * (0.15 + radius_diff * 0.05)
                z = self.PARTICLE_SPAWN_Z
                speed = random.random() * 0.3 + 0.1

                self.particles[index] = [x, y, z, speed]

    def stop(self):
        # clean up the display. after stopping the main loop has to be called once more
        self.display.stop()
        self.display.loop_running()
        self.display.destroy()
        self.x11.terminate()
        self.cava.release()
