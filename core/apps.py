"""Contains the core app configuration."""

from django.apps import AppConfig
from watson import search as watson


class CoreConfig(AppConfig):
    """This is the configuration for the core app."""

    name = "core"

    def ready(self) -> None:
        watson.register(
            self.get_model("ArchivedSong"),
            fields=("url", "artist", "title", "queries__query"),
            store=("id", "title", "url", "artist"),
        )
        watson.register(
            self.get_model("ArchivedPlaylist"),
            fields=("title", "queries__query"),
            store=("id", "title", "counter"),
        )
