"""Controls the Raspberry Pi's internal LEDs."""
import os
import subprocess


def _control_led(led: str, action: str) -> None:
    control_led = "/usr/local/sbin/raveberry/control_led"
    if os.path.isfile(control_led):
        subprocess.call(["sudo", control_led, led, action], stderr=subprocess.DEVNULL)


def enable_act_led() -> None:
    """Enables the green activity led on a Raspberry Pi."""
    _control_led("act", "enable")


def disable_act_led() -> None:
    """Disables the green activity led on a Raspberry Pi."""
    _control_led("act", "disable")


def enable_pwr_led() -> None:
    """Enables the red power led on a Raspberry Pi."""
    _control_led("pwr", "enable")


def disable_pwr_led() -> None:
    """Disables the red power led on a Raspberry Pi."""
    _control_led("pwr", "disable")
