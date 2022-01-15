"""This module provides app wide utility functions."""
import subprocess
from contextlib import contextmanager
from typing import List, Tuple

from django.http import HttpResponseForbidden


@contextmanager
def optional(condition, context_manager):
    if condition:
        with context_manager:
            yield
    else:
        yield


def camelize(snake_dict: dict) -> dict:
    def camelize_str(snake: str) -> str:
        head, *tail = snake.split("_")
        return head + "".join(word.capitalize() for word in tail)

    return {camelize_str(k): v for k, v in snake_dict.items()}


def get_devices() -> List[str]:
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
    output = subprocess.check_output(
        f"ip -o -f inet addr show {device}".split(), universal_newlines=True
    )
    words = output.split()
    return words[5]


def service_installed(service: str) -> bool:
    if not service.endswith(".service"):
        service += ".service"
    out = subprocess.run(
        ["systemctl", "list-unit-files", service],
        universal_newlines=True,
        stdout=subprocess.PIPE,
    ).stdout
    return len(out.splitlines()) > 3


def csrf_failure(request, reason="", template_name=""):
    return HttpResponseForbidden("Please reload")


def format_resolution(resolution: Tuple[int]) -> str:
    return "{}x{}".format(*resolution)
