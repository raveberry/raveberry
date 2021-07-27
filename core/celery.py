"""This module contains the celery app."""
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")

app = Celery("core")

app.config_from_object("django.conf:settings")


class CeleryNotReachable(Exception):
    """Raised when celery should be reachable but is not."""

    pass


def start() -> None:
    """Initializes celery."""
    # check if celery is up and wait for a maximum of 5 seconds
    for _ in range(10):
        if app.control.ping(timeout=0.5):
            break
    else:
        raise CeleryNotReachable("Celery worker pool not reachable. Is it running?")

    # stop running celery tasks from old django instance
    active_tasks = app.control.inspect().active()
    if active_tasks:
        for hostname, tasks in active_tasks.items():
            for task in tasks:
                app.control.revoke(task_id=task["id"], terminate=True)
