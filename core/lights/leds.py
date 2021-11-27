"""Controls the Raspberry Pi's internal LEDs."""
import subprocess


def _control_led(led: str, action: str) -> None:
    try:
        subprocess.call(
            ["sudo", "/usr/local/sbin/raveberry/control_led", led, action],
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass


def enable_act_led() -> None:
    _control_led("act", "enable")


def disable_act_led() -> None:
    _control_led("act", "disable")


def enable_pwr_led() -> None:
    _control_led("pwr", "enable")


def disable_pwr_led() -> None:
    _control_led("pwr", "disable")
