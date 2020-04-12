from threading import Thread

from django.db import connection


def background_thread(function):
    def decorator(*args, **kwargs):
        def run_and_close_connection():
            function(*args, **kwargs)
            connection.close()
        t = Thread(target=run_and_close_connection, daemon=True)
        t.start()
        return t
    return decorator
