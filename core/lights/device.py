"""This module contains the device superclass."""


class Device:
    """A class representing a visualization device that Raveberry can control."""

    def __init__(self, lights, name) -> None:
        self.lights = lights
        self.name = name
        self.brightness = 1.0
        self.monochrome = False
        self.initialized = False
        self.last_program = self.lights.disabled_program
        self.program = self.lights.disabled_program

    def load_program(self) -> None:
        last_program_name = self.lights.base.settings.get_setting(
            f"last_{self.name}_program", "Disabled"
        )
        program_name = self.lights.base.settings.get_setting(
            f"{self.name}_program", "Disabled"
        )

        self.last_program = self.lights.all_programs[last_program_name]
        # only enable if the device is initialized
        if self.initialized:
            self.program = self.lights.all_programs[program_name]

        self.program.use()

    def clear(self) -> None:
        """Resets this device, clearing all visualization."""
        raise NotImplementedError()
