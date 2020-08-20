"""This module provides app wide utility functions."""
import subprocess
from threading import Thread
from typing import Callable, Any, List

from django.core.handlers.wsgi import WSGIRequest
from django.db import connection
from django.http import HttpResponseForbidden, HttpResponse


def background_thread(function: Callable) -> Callable[..., Thread]:
    """This decorator makes the decorated function run in a background thread.
    These functions return immediately.
    After the thread finished, their database connection is closed."""

    def decorator(*args: Any, **kwargs: Any) -> Thread:
        def run_and_close_connection() -> None:
            function(*args, **kwargs)
            connection.close()

        thread = Thread(target=run_and_close_connection, daemon=True)
        thread.start()
        return thread

    return decorator


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


def csrf_failure(_request: WSGIRequest, reason: str = "") -> HttpResponse:
    return HttpResponseForbidden("Please reload")
