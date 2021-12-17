"""This module contains the device superclass."""
from core import redis
from core.settings import storage


class Device:
    """A class representing a visualization device that Raveberry can control."""

    def __init__(self, manager, name) -> None:
        self.manager = manager
        self.name = name
        self.brightness = storage.get(f"{self.name}_brightness")
        self.monochrome = storage.get(f"{self.name}_monochrome")
        self.initialized = False
        redis.set(f"{self.name}_initialized", False)
        self.program = None

    def load_program(self) -> None:
        """Load and activate this device's program from the database."""
        program_name = storage.get(f"{self.name}_program")

        # only enable if the device is initialized
        if self.initialized:
            self.program = self.manager.all_programs[program_name]
        else:
            self.program = self.manager.disabled_program

        self.program.use()

    def clear(self) -> None:
        """Resets this device, clearing all visualization."""
        raise NotImplementedError()
