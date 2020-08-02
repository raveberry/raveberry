"""This module registers all for the admin page so they are visible in the interface."""

from django.contrib import admin

import core.models as models

# Register your models here.
for model in [
    models.Tag,
    models.Counter,
    models.QueuedSong,
    models.CurrentSong,
    models.ArchivedSong,
    models.ArchivedPlaylist,
    models.PlaylistEntry,
    models.ArchivedQuery,
    models.ArchivedPlaylistQuery,
    models.Setting,
    models.RequestLog,
    models.PlayLog,
]:
    admin.site.register(model)
