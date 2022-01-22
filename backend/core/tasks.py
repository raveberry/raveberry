"""This module contains the celery app."""
import os
from threading import Thread
from typing import Any, Callable

from core.util import strtobool

app: Any

if strtobool(os.environ.get("DJANGO_NO_CELERY", "0")):
    # For debugging, celery's startup is quite slow, especially when reloading on every change.
    # Instead, use Threads to keep asynchronicity but with a much faster startup.
    CELERY_ACTIVE = False

    class MockCelery:
        """A mock class that starts threads instead of dispatching the tasks to celery workers."""

        def task(self, function: Callable) -> Callable:
            """This decorator mocks celery's delay function.
            This delay() creates a thread and starts it."""

            def delay(*args: Any, **kwargs: Any) -> None:
                thread = Thread(target=function, args=args, kwargs=kwargs, daemon=True)
                thread.start()

            # monkeypatch-add this method
            function.delay = delay  # type: ignore[attr-defined]

            return function

    def start() -> None:
        """MockCelery does not need to be initialized."""

    app = MockCelery()
else:
    CELERY_ACTIVE = True

    from celery import Celery

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")

    app = Celery("core")

    app.config_from_object("django.conf:settings")

    class CeleryNotReachable(Exception):
        """Raised when celery should be reachable but is not."""

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
            for _, tasks in active_tasks.items():
                for task in tasks:
                    app.control.revoke(task_id=task["id"], terminate=True)
