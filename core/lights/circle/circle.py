"""Handles the rendering of the circle visualization."""

# hack to allow direct calling of this script
# pylint: disable=wrong-import-position
# we need to access non-public pi3d members
# pylint: disable=protected-access
from __future__ import annotations

from typing import List, TYPE_CHECKING, Dict, no_type_check

if __name__ == "__main__":
    import sys

    sys.path.insert(0, "../../../")

import ctypes
import math
import os
import random
import subprocess
import time

from django.conf import settings

from core.lights.programs import ScreenProgram
from core.lights.screen import RenderingStoppedException

if TYPE_CHECKING:
    from core.lights.lights import Lights
    import pi3d
    import numpy as np


class Circle(ScreenProgram):
    """This class is responsible for rendering the circle screen visualization."""

    # The number of ffts that are kept in history
    FFT_HIST = 32
    # The part of the spectrum that is used to detect loud bass, making the circle bigger
    BASS_MAX = 0.05
    # The number of bins we cut after smoothing on both sides
    SPECTRUM_CUT = 2
    # The amount of particles
    NUM_PARTICLES = 400
    # Size of the particles
    PARTICLE_SIZE = 0.01
    # How far away to spawn particles
    PARTICLE_SPAWN_Z = 2.0
    # The size of dynamic modifications to the scale
    SCALE_STEP = 0.5

    def __init__(self, lights: "Lights") -> None:
        super().__init__(lights)
        self.name = "Circular"
        self.cava = lights.cava_program

        # To have pi3d display shader compilation errors, set the logging level to INFO
        # import logging
        # logging.basicConfig(level=logging.INFO)

        # The appearance of the shader was taken from
        # https://www.shadertoy.com/view/llycWD

        # The width and height of the displayed visualizer in pixels
        self.width = 640
        self.height = 480
        self.scale = 0.0

        self.should_prepare = False
        self.resolution_increases: Dict[float, int] = {}
        self.history_toggle = True

        self.total_bass = 0.0
        self.last_loop = 0.0
        self.time_elapsed = 0.0
        self.alarm_factor = 0.0
        self.bass_fraction = 0.0
        self.time_delta = 0.0
        self.bass_value = 0.0
        self.uniform_values: Dict[int, float] = {}

        # These initialisations are deferred into the _prepare function
        # that is called during the first draw(). Thus, ignore their type.
        self.fft: np.ndarray = None  # type: ignore
        self.display: pi3d.Display.Display = None  # type: ignore
        self.background: pi3d.Sprite = None  # type: ignore
        self.particle_shader: pi3d.Shader = None  # type: ignore
        self.particle_sprite: pi3d.Sprite = None  # type: ignore
        self.instance_vbo: ctypes._CData = None  # type: ignore # pylint: disable=no-member
        self.spectrum: pi3d.Sprite = None  # type: ignore
        self.logo: pi3d.Sprite = None  # type: ignore
        self.logo_array: np.ndarray = None  # type: ignore
        self.dynamic_texture: pi3d.Texture = None  # type: ignore
        self.after: pi3d.Sprite = None  # type: ignore
        self.post: pi3d.util.OffscreenTexture.OffscreenTexture = None  # type: ignore # pylint: disable=no-member
        self.post_sprite: pi3d.Sprite = None  # type: ignore

        # https://stackoverflow.com/questions/48472285/create-core-context-with-glut-freeglut
        # In order to use newer OpenGL versions (e.g. for Instancing), use the following line:
        # glutInitContextVersion( 3, 3 );

    def _set_resolution(self, width: int, height: int) -> None:
        self.width, self.height = width, height
        # this scale value determines how many times bigger the actual display is
        # in comparison to the actually computed buffer.
        # Higher values equal lower computation but also lower resolution.
        # 1366x768 works alright, use it to compute a starting SCALE (in multiples of SCALE_STEP)
        self.scale = round(width * height / (1366 * 768) * 1 / self.SCALE_STEP) / (
            1 / self.SCALE_STEP
        )
        self.scale = max(self.scale, 1)

    def start(self) -> None:
        self.cava.use()

        os.environ["DISPLAY"] = ":0"

        # disable blanking and power saving
        subprocess.call("xset s off".split())
        subprocess.call("xset s noblank".split())
        subprocess.call("xset -dpms".split())

        # read the resolution from the X window and set our dimensions accordingly.
        # Uses the DISPLAY environ variable
        # alternative without X would be tvserice -d edid.dat && edidparser edid.dat
        xwininfo = (
            subprocess.check_output("xwininfo -root".split()).decode().splitlines()
        )
        width, height = 640, 480
        for line in xwininfo:
            line = line.strip()
            if line.startswith("Width:"):
                width = int(line.split()[1])
            if line.startswith("Height:"):
                height = int(line.split()[1])
        # width, height = 640, 360
        self._set_resolution(width, height)
        self.resolution_increases = {}
        self.should_prepare = True
        self.history_toggle = True

    def increase_resolution(self) -> None:
        if self.scale == 1:
            # do not render more than one pixel per pixel
            return

        # if we get told to increase at a specific resolution a lot of times,
        # we got probably caught in an oscillation. Don't increase resolution then
        scale_key = round(self.scale, 1)
        if scale_key not in self.resolution_increases:
            self.resolution_increases[scale_key] = 0
        if self.resolution_increases[scale_key] >= 2:
            return
        self.resolution_increases[scale_key] += 1

        self.scale = max(1, self.scale - self.SCALE_STEP)

    def decrease_resolution(self) -> None:
        self.scale += self.SCALE_STEP

    def _prepare(self) -> None:
        self.should_prepare = False

        import numpy as np

        # pi3d has to be imported in the same thread that it will draw in
        # Thus, import it here instead of at the top of the file
        import pi3d
        from pi3d.util.OffScreenTexture import OffScreenTexture
        from pi3d.constants import opengles, GL_CLAMP_TO_EDGE, GL_ALWAYS

        # used for reimplementing the draw call with instancing
        from pi3d.constants import (
            GLsizei,
            GLint,
            GLboolean,
            GL_FLOAT,
            GLuint,
            GL_ARRAY_BUFFER,
            GL_STATIC_DRAW,
            GLfloat,
        )
        from PIL import Image

        # Setup display and initialise pi3d
        self.display = pi3d.Display.create(
            w=self.width, h=self.height, window_title="Raveberry"  # , use_glx=True
        )
        # error 0x500 after Display create
        # error = opengles.glGetError()
        # Set a pink background color so mistakes are clearly visible
        # self.display.set_background(1, 0, 1, 1)

        # with an alpha value of 1 flat glx renders the window transparently for some reason
        # so instead we use a value slightly smaller than 1
        # self.display.set_background(0, 0, 0, 0.999)
        self.display.set_background(0, 0, 0, 1)

        # print OpenGL Version, useful for debugging
        # import ctypes

        # from pi3d.constants import GL_VERSION

        # def print_char_p(addr):
        #     g = (ctypes.c_char * 32).from_address(addr)
        #     i = 0
        #     while True:
        #         try:
        #             c = g[i]
        #         except IndexError:
        #             break
        #         if c == b"\x00":
        #             break
        #         sys.stdout.write(c.decode())
        #         i += 1
        #     sys.stdout.write("\n")

        # print_char_p(opengles.glGetString(GL_VERSION))

        # Visualization is split into five parts:
        # The background, the particles, the spectrum, the logo and after effects.
        # * The background is a vertical gradient that cycles through HSV color space,
        #     speeding up with strong bass.
        # * Particles are multiple sprites that are created at a specified x,y-coordinate
        #     and fly towards the camera.
        #     Due to the projection into screenspace they seem to move away from the center.
        # * The spectrum is a white circle that represents the fft-transformation of the
        #     currently played audio. It is smoothed to avoid strong spikes.
        # * The logo is a black circle on top of the spectrum containing the logo.
        # * After effects add a vignette.
        # Each of these parts is represented with pi3d Shapes.
        # They have their own shader and are ordered on the z-axis to ensure correct overlapping.

        background_shader = pi3d.Shader(
            os.path.join(settings.BASE_DIR, "core/lights/circle/background")
        )
        self.background = pi3d.Sprite(w=2, h=2)
        self.background.set_shader(background_shader)
        self.background.positionZ(0)

        self.particle_shader = pi3d.Shader(
            os.path.join(settings.BASE_DIR, "core/lights/circle/particle")
        )

        # create one sprite for all particles
        self.particle_sprite = pi3d.Sprite(w=self.PARTICLE_SIZE, h=self.PARTICLE_SIZE)
        self.particle_sprite.set_shader(self.particle_shader)
        self.particle_sprite.positionZ(0)
        # this array containes the position and speed for all particles
        particles = self._initial_particles()

        # This part was modified from https://learnopengl.com/Advanced-OpenGL/Instancing
        self.instance_vbo = GLuint()
        opengles.glGenBuffers(GLsizei(1), ctypes.byref(self.instance_vbo))
        opengles.glBindBuffer(GL_ARRAY_BUFFER, self.instance_vbo)
        particles_raw = particles.ctypes.data_as(ctypes.POINTER(GLfloat))
        opengles.glBufferData(
            GL_ARRAY_BUFFER, particles.nbytes, particles_raw, GL_STATIC_DRAW
        )
        opengles.glBindBuffer(GL_ARRAY_BUFFER, GLuint(0))

        attr_particle = opengles.glGetAttribLocation(
            self.particle_shader.program, b"particle"
        )
        opengles.glEnableVertexAttribArray(attr_particle)
        opengles.glBindBuffer(GL_ARRAY_BUFFER, self.instance_vbo)
        opengles.glVertexAttribPointer(
            attr_particle, GLint(4), GL_FLOAT, GLboolean(0), 0, 0
        )
        opengles.glBindBuffer(GL_ARRAY_BUFFER, GLuint(0))
        opengles.glVertexAttribDivisor(attr_particle, GLuint(1))

        spectrum_shader = pi3d.Shader(
            os.path.join(settings.BASE_DIR, "core/lights/circle/spectrum")
        )

        # use the ratio to compute small sizes for the sprites
        ratio = self.width / self.height
        self.spectrum = pi3d.Sprite(w=2 / ratio, h=2)
        self.spectrum.set_shader(spectrum_shader)
        self.spectrum.positionZ(0)

        # initialize the spectogram history with zeroes
        self.fft = np.zeros(
            (self.FFT_HIST, self.cava.bars - 2 * self.SPECTRUM_CUT), dtype=np.uint8
        )

        logo_shader = pi3d.Shader(
            os.path.join(settings.BASE_DIR, "core/lights/circle/logo")
        )
        self.logo = pi3d.Sprite(w=1.375 / ratio, h=1.375)
        self.logo.set_shader(logo_shader)
        self.logo.positionZ(0)

        logo_image = Image.open(
            os.path.join(settings.STATIC_FILES, "graphics/raveberry_square.png")
        )
        self.logo_array = np.frombuffer(logo_image.tobytes(), dtype=np.uint8)
        self.logo_array = self.logo_array.reshape(
            (logo_image.size[1], logo_image.size[0], 3)
        )
        # add space for the spectrum
        self.logo_array = np.concatenate(
            (
                self.logo_array,
                np.zeros((self.FFT_HIST, logo_image.size[0], 3), dtype=np.uint8),
            ),
            axis=0,
        )
        # add alpha channel
        self.logo_array = np.concatenate(
            (
                self.logo_array,
                np.ones(
                    (self.logo_array.shape[0], self.logo_array.shape[1], 1),
                    dtype=np.uint8,
                ),
            ),
            axis=2,
        )

        # In order to save memory, the logo and the spectrum share one texture.
        # The upper 256x256 pixels are the raveberry logo.
        # Below are 256xFFT_HIST pixels for the spectrum.
        # The lower part is periodically updated every frame while the logo stays static.
        self.dynamic_texture = pi3d.Texture(self.logo_array)
        # Prevent interpolation from opposite edge
        self.dynamic_texture.m_repeat = GL_CLAMP_TO_EDGE
        self.spectrum.set_textures([self.dynamic_texture])
        self.logo.set_textures([self.dynamic_texture])

        after_shader = pi3d.Shader(
            os.path.join(settings.BASE_DIR, "core/lights/circle/after")
        )
        self.after = pi3d.Sprite(w=2, h=2)
        self.after.set_shader(after_shader)
        self.after.positionZ(0)

        # create an OffscreenTexture to allow scaling.
        # By first rendering into a smaller Texture a lot of computation is saved.
        # This OffscreenTexture is then drawn at the end of the draw loop.
        self.post = OffScreenTexture("scale")
        self.post_sprite = pi3d.Sprite(w=2, h=2)
        post_shader = pi3d.Shader(
            os.path.join(settings.BASE_DIR, "core/lights/circle/scale")
        )
        self.post_sprite.set_shader(post_shader)
        self.post_sprite.set_textures([self.post])

        self.total_bass = 0
        self.last_loop = time.time()
        self.time_elapsed = 0

        opengles.glDepthFunc(GL_ALWAYS)

    def _set_unif(self, sprite: "pi3d.Sprite", uniforms: List[int]) -> None:
        for uniform in uniforms:
            sprite.unif[uniform] = self.uniform_values[uniform]

    def draw(self) -> None:
        """Renders one frame of the visualization.
        Raises a RenderingStoppedException if pi3d does no rendering anymore.
        (most probably because the window was closed)"""
        import numpy as np
        from scipy.ndimage.filters import gaussian_filter
        from pi3d.Camera import Camera
        from pi3d.constants import (
            opengles,
            GL_SRC_ALPHA,
            GL_ONE_MINUS_SRC_ALPHA,
            GLsizei,
            GLboolean,
            GLint,
            GL_FLOAT,
            GL_ARRAY_BUFFER,
            GL_UNSIGNED_SHORT,
            GL_TEXTURE_2D,
            GL_UNSIGNED_BYTE,
        )

        time_logging = False

        if self.should_prepare:
            self._prepare()

        if self.lights.alarm_program.factor != -1:
            self.alarm_factor = max(0.001, self.lights.alarm_program.factor)
        else:
            self.alarm_factor = 0

        then = time.time()

        # loop_running does all of pi3d's logic and needs to be called every frame
        if not self.display.loop_running():
            raise RenderingStoppedException

        now = self.display.time
        self.time_delta = now - self.last_loop
        self.last_loop = now
        self.time_elapsed += self.time_delta

        if time_logging:
            print(f"{time.time() - then} main loop")
            then = time.time()

        # use a sliding window to smooth the spectrum with a gauss function
        # truncating does not save significant time (~3% for this step)

        # new_frame = np.array(self.cava.current_frame, dtype="float32")
        new_frame = gaussian_filter(self.cava.current_frame, sigma=1.5, mode="nearest")
        new_frame = new_frame[self.SPECTRUM_CUT : -self.SPECTRUM_CUT]
        new_frame = -0.5 * new_frame ** 3 + 1.5 * new_frame
        new_frame *= 255
        current_frame = new_frame

        if time_logging:
            print(f"{time.time() - then} spectrum smoothing")
            then = time.time()

        # Value used for circle shake and background color cycle
        # select the first few values and compute their average
        bass_elements = math.ceil(self.BASS_MAX * self.cava.bars)
        self.bass_value = sum(current_frame[0:bass_elements]) / bass_elements / 255
        self.bass_value = max(self.bass_value, self.alarm_factor)
        self.total_bass = self.total_bass + self.bass_value
        # the fraction of time that there was bass
        self.bass_fraction = self.total_bass / self.time_elapsed / self.lights.UPS

        self.uniform_values = {
            48: self.width / self.scale,
            49: self.height / self.scale,
            50: self.scale,
            51: self.FFT_HIST,
            52: self.NUM_PARTICLES,
            53: self.PARTICLE_SPAWN_Z,
            54: self.time_elapsed,
            55: self.time_delta,
            56: self.alarm_factor,
            57: self.bass_value,
            58: self.total_bass,
            59: self.bass_fraction,
        }

        # start rendering to the smaller OffscreenTexture
        # we decrease the size of the texture so it only allocates that much memory
        # otherwise it would use as much as the displays size, negating its positive effect
        self.post.ix = int(self.post.ix / self.scale)
        self.post.iy = int(self.post.iy / self.scale)
        opengles.glViewport(
            GLint(0),
            GLint(0),
            GLsizei(int(self.width / self.scale)),
            GLsizei(int(self.height / self.scale)),
        )
        self.post._start()
        self.post.ix = self.width
        self.post.iy = self.height

        self._set_unif(self.background, [48, 49, 54, 56, 58])
        self.background.draw()

        if time_logging:
            print(f"{time.time() - then} background draw")
            then = time.time()

        # enable additive blending so the draw order of overlapping particles does not matter
        opengles.glBlendFunc(1, 1)

        self._set_unif(self.particle_sprite, [53, 54, 59])

        # copied code from pi3d.Shape.draw()
        # we don't need modelmatrices, normals ord textures and always blend
        self.particle_sprite.load_opengl()
        camera = Camera.instance()
        if not camera.mtrx_made:
            camera.make_mtrx()
        self.particle_sprite.MRaw = self.particle_sprite.tr1
        self.particle_sprite.M[0, :, :] = self.particle_sprite.MRaw[:, :]
        self.particle_sprite.M[1, :, :] = np.dot(
            self.particle_sprite.MRaw, camera.mtrx
        )[:, :]

        # Buffer.draw()
        buf = self.particle_sprite.buf[0]
        buf.load_opengl()
        shader = buf.shader
        shader.use()
        opengles.glUniformMatrix4fv(
            shader.unif_modelviewmatrix,
            GLsizei(2),
            GLboolean(0),
            self.particle_sprite.M.ctypes.data,
        )
        opengles.glUniform3fv(shader.unif_unif, GLsizei(20), self.particle_sprite.unif)
        buf._select()
        opengles.glVertexAttribPointer(
            shader.attr_vertex, GLint(3), GL_FLOAT, GLboolean(0), buf.N_BYTES, 0
        )
        opengles.glEnableVertexAttribArray(shader.attr_vertex)
        opengles.glVertexAttribPointer(
            shader.attr_texcoord, GLint(2), GL_FLOAT, GLboolean(0), buf.N_BYTES, 24
        )
        opengles.glEnableVertexAttribArray(shader.attr_texcoord)
        buf.disp.last_shader = shader
        opengles.glUniform3fv(shader.unif_unib, GLsizei(5), buf.unib)

        opengles.glBindBuffer(GL_ARRAY_BUFFER, self.instance_vbo)
        opengles.glDrawElementsInstanced(
            buf.draw_method,
            GLsizei(buf.ntris * 3),
            GL_UNSIGNED_SHORT,
            0,
            self.NUM_PARTICLES,
        )

        # restore normal blending
        opengles.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        if time_logging:
            print(f"{time.time() - then} particle draw")
            then = time.time()

        # roll the history one further, insert the current one.
        # we use a texture with four channels eventhough we only need one, refer to this post:
        # https://community.khronos.org/t/updating-textures-per-frame/75020/3
        # basically the gpu converts it anyway, so other formats would be slower
        history = np.zeros(
            (self.FFT_HIST, self.cava.bars - 2 * self.SPECTRUM_CUT, 4), dtype="uint8"
        )
        self.fft = np.roll(self.fft, 1, 0)
        self.fft[0] = current_frame
        history[:, :, 0] = self.fft

        if time_logging:
            print(f"{time.time() - then} spectrum roll")
            then = time.time()

        # change the spectrum part of the texture (the lower 256xFFT_HIST pixels)
        opengles.glBindTexture(GL_TEXTURE_2D, self.dynamic_texture._tex)
        iformat = self.dynamic_texture._get_format_from_array(
            history, self.dynamic_texture.i_format
        )
        opengles.glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            0,
            self.dynamic_texture.ix,
            history.shape[1],
            history.shape[0],
            iformat,
            GL_UNSIGNED_BYTE,
            history.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),
        )

        if time_logging:
            print(f"{time.time() - then} glTexImage2D")
            then = time.time()

        self._set_unif(self.spectrum, [48, 49, 51, 52, 53, 54, 55, 57, 58])
        self.spectrum.draw()

        if time_logging:
            print(f"{time.time() - then} spectrum draw")
            then = time.time()

        self._set_unif(self.logo, [48, 49, 51, 54, 57, 58])
        self.logo.draw()

        if time_logging:
            print(f"{time.time() - then} logo draw")
            then = time.time()

        self._set_unif(self.after, [48, 49, 54, 57])
        self.after.draw()

        if time_logging:
            print(f"{time.time() - then} after draw")
            then = time.time()

        self.post._end()

        opengles.glViewport(
            GLint(0), GLint(0), GLsizei(self.width), GLsizei(self.height)
        )
        self._set_unif(self.post_sprite, [50])
        self.post_sprite.draw()

        if time_logging:
            print(f"{time.time() - then} post draw")
            print(f"scale: {self.scale}")
            print("=====")

    def _initial_particles(self) -> np.ndarray:
        """ constructs an array of particles containing x, y and speed value for each particle """
        import numpy as np

        particles = np.zeros((self.NUM_PARTICLES, 4), dtype="float32")
        for index in range(particles.shape[0]):
            # Generate random particle
            phi = random.random() * 2 * math.pi
            radius_diff = random.random()
            x = math.cos(phi) * (0.2 + radius_diff * 0.05)
            y = math.sin(phi) * (0.15 + radius_diff * 0.05)
            z = self.PARTICLE_SPAWN_Z
            speed = 0.15 * (random.random() * 0.75 + 0.3)
            offset = random.random() * z

            particles[index] = [x, y, speed, offset]
        return particles

    def stop(self) -> None:
        # clean up the display. after stopping the main loop has to be called once more
        self.display.stop()
        # loop running calls destroy after being stopped, no need to do it explicitly
        self.display.loop_running()
        self.cava.release()


@no_type_check  # don't make mypy deal with dynamic classes
def main() -> None:
    """Runs this visualization without the need of the server running."""
    mock_cava = type(
        "obj",
        (object,),
        {
            "bars": 199,
            "current_frame": [0 for _ in range(199)],
            "use": lambda: ...,
            "release": lambda: ...,
        },
    )
    mock_lights = type(
        "obj",
        (object,),
        {
            "UPS": 25,
            "cava_program": mock_cava,
            "alarm_program": type("obj", (object,), {"factor": -1}),
        },
    )
    circle = Circle(mock_lights)
    circle.start()
    seconds_per_frame = 1 / mock_lights.UPS

    while True:
        computation_start = time.time()
        try:
            circle.draw()
        except RenderingStoppedException:
            break
        mock_cava.current_frame = [
            0.5 * (1 + math.sin(-4 * circle.time_elapsed + 0.5 * i))
            for i in range(len(mock_cava.current_frame))
        ]
        mock_cava.current_frame = [
            0.8
            * 0.5
            * (1 + math.sin(4 * circle.time_elapsed))
            * 0.5
            * (1 + math.sin(-4 * circle.time_elapsed + 0.2 * i))
            for i in range(len(mock_cava.current_frame))
        ]
        computation_time = time.time() - computation_start
        # print(f'time needed / avaliable: {computation_time / seconds_per_frame:0.2f}')
        try:
            time.sleep(seconds_per_frame - computation_time)
        except ValueError:
            pass


if __name__ == "__main__":
    # overwrite the settings to have it point to the correct directories
    settings = type(  # type: ignore # pylint: disable=invalid-name
        "obj", (object,), {"BASE_DIR": "../../..", "STATIC_FILES": "../../../static"}
    )
    main()
