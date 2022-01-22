"""This module contains all programs that use the screen."""
import logging
import os
import subprocess
import time
from typing import List, TYPE_CHECKING, Optional

from django.conf import settings as conf
from core import redis
from core.lights import lights
from core.lights.exceptions import ScreenProgramStopped
from core.lights.programs import ScreenProgram

if TYPE_CHECKING:
    from core.lights.worker import DeviceManager


class Video(ScreenProgram):
    """Plays a given Video."""

    def __init__(self, manager: "DeviceManager", video: str, loop=False):
        super().__init__(manager, os.path.splitext(os.path.basename(video))[0])
        self.player: Optional[subprocess.Popen] = None
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
                except FileNotFoundError as error:
                    raise ValueError("No video player found") from error

    def compute(self) -> None:
        if not self.player or self.player.poll() is not None:
            raise ScreenProgramStopped

    def stop(self) -> None:
        if not self.player:
            return
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
        """Returns all possible visualization variants by listing the available shaders."""
        # don't offer this feature on raspberry pi 3
        try:
            with open("/proc/device-tree/model", encoding="utf-8") as model_file:
                model = model_file.read()
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
        super().__init__(manager, variant)
        # __init__ is called for every variant reported by get_variants
        # that method acts as a guard that the module is installed
        import raveberry_visualization

        self.controller = raveberry_visualization.Controller()
        self.last_fps_check = time.time()

    def start(self) -> None:
        self.manager.utilities.cava.use()
        self.controller.start(
            self.name,
            self.manager.settings["ups"],
            Visualization.NUM_PARTICLES,
            Visualization.FPS_MEASURE_WINDOW,
        )

    def compute(self) -> None:
        now = time.time()
        if now - self.last_fps_check > Visualization.FPS_MEASURE_WINDOW / 2:
            self.last_fps_check = now
            current_fps = self.controller.get_fps()
            redis.put("current_fps", current_fps)
            if (
                self.manager.settings["dynamic_resolution"]
                and current_fps < 0.9 * self.manager.settings["ups"]
            ):
                self.manager.devices.screen.lower_resolution()
                # restart the program with the new resolution
                self.manager.restart_screen_program(sleep_time=2, has_lock=True)
            else:
                lights.update_state()
        if not self.controller.is_active():
            raise ScreenProgramStopped
        self.controller.set_parameters(
            self.manager.utilities.alarm.factor,
            self.manager.utilities.cava.current_frame,
        )

    def stop(self) -> None:
        self.controller.stop()
        self.manager.utilities.cava.release()
