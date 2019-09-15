from django.contrib import admin

import core.models as models

# Register your models here.
admin.site.register(models.Tag)
admin.site.register(models.Counter)
admin.site.register(models.Pad)
admin.site.register(models.QueuedSong)
admin.site.register(models.CurrentSong)
admin.site.register(models.ArchivedSong)
admin.site.register(models.ArchivedPlaylist)
admin.site.register(models.PlaylistEntry)
admin.site.register(models.ArchivedQuery)
admin.site.register(models.ArchivedPlaylistQuery)
admin.site.register(models.Setting)
admin.site.register(models.RequestLog)
admin.site.register(models.PlayLog)
