"""This module contains all programs that use the screen."""
import logging
import os
import subprocess
import time
from typing import List

import main.settings as conf
from core import redis
from core.lights import lights
from core.lights.exceptions import ScreenProgramStopped
from core.lights.programs import ScreenProgram


class Video(ScreenProgram):
    def __init__(self, manager: "DeviceManager", video: str, loop=False):
        super().__init__(manager)
        self.name = os.path.splitext(os.path.basename(video))[0]
        self.player = None
        if not os.path.isabs(video):
            video = os.path.join(conf.BASE_DIR, "resources", "videos", video)
        if not os.path.isfile(video):
            logging.warning("video %s does not exist", video)
            raise ValueError(f"video {video} does not exist")
        self.video = video
        self.loop = loop
        self.omxplayer = False

    def start(self) -> None:
        # omxplayer is preferred because it loops smoothly and is hardware accelerated
        try:
            args = ["omxplayer", self.video]
            if self.loop:
                args.append("--loop")
            self.player = subprocess.Popen(
                args, stdout=subprocess.DEVNULL, stdin=subprocess.PIPE
            )
            self.omxplayer = True
        except FileNotFoundError:
            # vlc is hardware accelerated, but shows a black screen between loops
            try:
                args = ["cvlc", "--fullscreen", "--no-video-title-show", self.video]
                if self.loop:
                    args.append("--loop")
                self.player = subprocess.Popen(args, stdout=subprocess.DEVNULL)
            except FileNotFoundError:
                # mplayer loops smoothly but is not hardware accelerated
                try:
                    args = ["mplayer", "-fs", self.video]
                    if self.loop:
                        args.append("-loop")
                        args.append("0")
                    self.player = subprocess.Popen(args, stdout=subprocess.DEVNULL)
                except FileNotFoundError:
                    raise ValueError("No video player found")

    def compute(self) -> None:
        if not self.player or self.player.poll() is not None:
            raise ScreenProgramStopped

    def stop(self) -> None:
        if self.omxplayer:
            # for some reason omxplayer refuses to exit on sigterm from python
            self.player.communicate(b"q")
        else:
            self.player.terminate()


class Visualization(ScreenProgram):
    """Renders a visualization to the screen."""

    NUM_PARTICLES = 400
    FPS_MEASURE_WINDOW = 20.0  # seconds

    @staticmethod
    def get_variants() -> List[str]:
        # don't offer this feature on raspberry pi 3
        try:
            with open("/proc/device-tree/model") as f:
                model = f.read()
                if model.startswith("Raspberry Pi 3"):
                    return []
        except FileNotFoundError:
            # we are not running on a raspberry pi
            pass

        try:
            import raveberry_visualization

            controller = raveberry_visualization.Controller()
            return controller.get_variants()
        except ModuleNotFoundError:
            return []

    def __init__(self, manager: "DeviceManager", variant: str) -> None:
        super().__init__(manager)
        # __init__ is called for every variant reported by get_variants
        # that method acts as a guard that the module is installed
        import raveberry_visualization

        self.name = variant
        self.controller = raveberry_visualization.Controller()
        self.last_fps_check = time.time()

    def start(self) -> None:
        self.manager.cava_program.use()
        self.controller.start(
            self.name,
            self.manager.ups,
            Visualization.NUM_PARTICLES,
            Visualization.FPS_MEASURE_WINDOW,
        )

    def compute(self) -> None:
        now = time.time()
        if now - self.last_fps_check > Visualization.FPS_MEASURE_WINDOW / 2:
            self.last_fps_check = now
            current_fps = self.controller.get_fps()
            redis.set("current_fps", current_fps)
            if self.manager.dynamic_resolution and current_fps < 0.9 * self.manager.ups:
                self.manager.screen.lower_resolution()
                # restart the program with the new resolution
                self.manager.restart_screen_program(sleep_time=2, has_lock=True)
            else:
                lights.update_state()
        if not self.controller.is_active():
            raise ScreenProgramStopped
        self.controller.set_parameters(
            self.manager.alarm_program.factor, self.manager.cava_program.current_frame
        )

    def stop(self) -> None:
        self.controller.stop()
        self.manager.cava_program.release()
