"""This module provides app wide utility functions."""

from threading import Thread
from typing import Callable, Any

from django.db import connection


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
