"""This module deals with the "celery" command.
It starts the celery worker and restarts them on file changes."""
import subprocess

from django.core.management.base import BaseCommand
from django.utils import autoreload


def restart_celery() -> None:
    """Kills all celery workers and starts new ones."""
    subprocess.call(["pkill", "-9", "-f", "celery -A core"])

    # https://docs.celeryproject.org/en/stable/userguide/tasks.html
    # use -O fair to be friendly to long-running tasks
    subprocess.call("celery -A core worker -O fair -l INFO".split())


class Command(BaseCommand):
    """Class to register the command"""

    def handle(self, *args, **options) -> None:
        print("Starting celery worker with autoreload...")
        autoreload.run_with_reloader(restart_celery)
