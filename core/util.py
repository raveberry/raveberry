"""This module provides app wide utility functions."""

from threading import Thread

from django.db import connection


def background_thread(function):
    """This decorator makes the decorated function run in a background thread.
    These functions return immediately.
    After the thread finished, their database connection is closed."""

    def decorator(*args, **kwargs):
        def run_and_close_connection():
            function(*args, **kwargs)
            connection.close()

        thread = Thread(target=run_and_close_connection, daemon=True)
        thread.start()
        return thread

    return decorator
