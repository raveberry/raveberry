"""This module provides app wide utility functions."""
import subprocess
from contextlib import contextmanager
from typing import List, Tuple, ContextManager, Generator

from django.http import (
    HttpResponseForbidden,
    HttpResponseBadRequest,
    HttpResponse,
    QueryDict,
)


def strtobool(value: str) -> bool:
    """Convert a string representation of a boolean to True or False."""
    value = value.lower()
    if value in ("y", "yes", "t", "true", "on", "1"):
        return True
    if value in ("n", "no", "f", "false", "off", "0"):
        return False
    raise ValueError(f"invalid truth value {value}")


@contextmanager
def optional(condition: bool, context_manager: ContextManager) -> Generator:
    """Conditionally apply a context_manager. If condition is false, no context manager is used."""
    if condition:
        with context_manager:
            yield
    else:
        yield


def camelize(snake_dict: dict) -> dict:
    """Transforms each key of the given dict from snake_case to CamelCase."""

    def camelize_str(snake: str) -> str:
        """Transforms a CamelCase string into a snake_case string."""
        head, *tail = snake.split("_")
        return head + "".join(word.capitalize() for word in tail)

    return {camelize_str(k): v for k, v in snake_dict.items()}


def extract_value(request: QueryDict) -> Tuple[str, HttpResponse]:
    """Return the "value" from the given QueryDict,
    and an HttpResponse if value is not None, or HttpResponseBadRequest if it is None."""
    value = request.get("value")
    if value is None:
        return "", HttpResponseBadRequest("value must be specified")
    return value, HttpResponse()


def get_devices() -> List[str]:
    """Returns a list of all network devices."""
    output = subprocess.check_output(
        "ip route show default".split(), universal_newlines=True
    )
    words = output.split()
    devices = []
    for cur, nex in zip(words, words[1:]):
        if cur == "dev":
            devices.append(nex)
    if not devices:
        raise ValueError("no devices found")
    return devices


def ip_of_device(device: str) -> str:
    """Returns the IP that the system has on the given network device."""
    output = subprocess.check_output(
        f"ip -4 a show dev {device}".split(), universal_newlines=True
    )
    ip = None
    for line in output.split("\n"):
        line = line.strip()
        if not line.startswith("inet"):
            continue
        ip = line.split()[1].split("/")[0]
        break
    if not ip:
        raise ValueError(f"ip not found for {device}")
    return ip


def broadcast_of_device(device: str) -> str:
    """Returns the broadcast address of the given network device."""
    output = subprocess.check_output(
        f"ip -o -f inet addr show {device}".split(), universal_newlines=True
    )
    words = output.split()
    return words[5]


def service_installed(service: str) -> bool:
    """Returns whether the given systemd service is installed."""
    if not service.endswith(".service"):
        service += ".service"
    try:
        out = subprocess.check_output(
            ["systemctl", "list-unit-files", service], text=True
        )
    except subprocess.CalledProcessError:
        return False
    return len(out.splitlines()) > 3


def csrf_failure(  # pylint: disable=unused-argument
    request, reason="", template_name=""
) -> HttpResponseForbidden:
    """A custom csrf failure view that fits inside a toast message."""
    return HttpResponseForbidden("Please reload")


def format_resolution(resolution: Tuple[int, int]) -> str:
    """Format an int-tuple as a readable resolution."""
    return f"{resolution[0]}x{resolution[1]}"
