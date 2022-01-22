"""This module contains the device superclass."""
from typing import cast

from core import redis
from core.redis import DeviceInitialized
from core.settings import storage
from core.settings.storage import DeviceBrightness, DeviceMonochrome
from core.lights.programs import LightProgram, Disabled


class Device:
    """A class representing a visualization device that Raveberry can control."""

    def __init__(self, manager, name) -> None:
        self.manager = manager
        self.name = name
        assert self.name in ["ring", "strip", "wled", "screen"]
        self.brightness = storage.get(cast(DeviceBrightness, f"{self.name}_brightness"))
        self.monochrome = storage.get(cast(DeviceMonochrome, f"{self.name}_monochrome"))
        self.initialized = False
        redis.put(cast(DeviceInitialized, f"{self.name}_initialized"), False)
        self.program: LightProgram = Disabled(manager)

    def load_program(self) -> None:
        """Load and activate this device's program from the database."""
        assert self.name in ["ring", "strip", "wled", "screen"]
        program_name = storage.get(cast(DeviceBrightness, f"{self.name}_program"))

        # only enable if the device is initialized
        if self.initialized:
            self.program = self.manager.programs[program_name]
        else:
            self.program = self.manager.utilities.disabled

        self.program.use()

    def clear(self) -> None:
        """Resets this device, clearing all visualization."""
        raise NotImplementedError()
