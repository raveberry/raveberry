from django.db import models
from django.contrib import admin
import core.musiq.song_queue
import core.musiq.song_utils as song_utils

# Create your models here.
class Tag(models.Model):
    text = models.CharField(max_length=100)
    def __str__(self):
        return self.text

class Counter(models.Model):
    value = models.IntegerField()
    def __str__(self):
        return str(self.value)

class ArchivedSong(models.Model):
    url = models.CharField(max_length=200, unique=True)
    artist = models.CharField(max_length=1000)
    title = models.CharField(max_length=1000)
    counter = models.IntegerField()
    def __str__(self):
        return self.title + ' (' + self.url + '): ' + str(self.counter)
    def displayname(self):
        return song_utils.displayname(self.artist, self.title)

class ArchivedPlaylist(models.Model):
    list_id = models.CharField(max_length=200)
    title = models.CharField(max_length=1000)
    created = models.DateTimeField(auto_now_add=True)
    counter = models.IntegerField()
    def __str__(self):
        return self.title + ': ' + str(self.counter)

class PlaylistEntry(models.Model):
    playlist = models.ForeignKey('ArchivedPlaylist', on_delete=models.CASCADE, related_name='entries')
    index = models.IntegerField()
    url = models.CharField(max_length=200)
    def __str__(self):
        return self.playlist.title + '[' + str(self.index) + ']: ' + self.url
    class Meta:
       ordering = ['playlist', 'index']

class ArchivedQuery(models.Model):
    song = models.ForeignKey('ArchivedSong', on_delete=models.CASCADE, related_name='queries')
    query = models.CharField(max_length=1000)
    def __str__(self):
        return self.query

class ArchivedPlaylistQuery(models.Model):
    playlist = models.ForeignKey('ArchivedPlaylist', on_delete=models.CASCADE, related_name='queries')
    query = models.CharField(max_length=1000)
    def __str__(self):
        return self.query

class QueuedSong(models.Model):
    index = models.IntegerField()
    manually_requested = models.BooleanField()
    votes = models.IntegerField(default=0)
    internal_url = models.CharField(max_length=200)
    external_url = models.CharField(max_length=200, blank=True)
    artist = models.CharField(max_length=1000)
    title = models.CharField(max_length=1000)
    duration = models.IntegerField()
    objects = core.musiq.song_queue.SongQueue()
    def __str__(self):
        return str(self.index) + ': ' + self.title + ' (' + self.internal_url + ')'
    def displayname(self):
        return song_utils.displayname(self.artist, self.title)
    class Meta:
       ordering = ['index']

class CurrentSong(models.Model):
    queue_key = models.IntegerField()
    manually_requested = models.BooleanField()
    votes = models.IntegerField()
    internal_url = models.CharField(max_length=200)
    external_url = models.CharField(max_length=200, blank=True)
    artist = models.CharField(max_length=1000)
    title = models.CharField(max_length=1000)
    duration = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.title + ' (' + self.internal_url + ')'
    def displayname(self):
        return song_utils.displayname(self.artist, self.title)

class RequestLog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    song = models.ForeignKey('ArchivedSong', on_delete=models.SET_NULL, blank=True, null=True)
    playlist = models.ForeignKey('ArchivedPlaylist', on_delete=models.SET_NULL, blank=True, null=True)
    address = models.CharField(max_length=50)
    def __str__(self):
        if self.song is not None:
            return self.address + ': ' + self.song.displayname()
        elif self.playlist is not None:
            return self.address + ': ' + self.playlist.title
        else:
            return self.address + ': <None>'

class PlayLog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    song = models.ForeignKey('ArchivedSong', on_delete=models.SET_NULL, blank=True, null=True)
    manually_requested = models.BooleanField()
    votes = models.IntegerField(null=True)
    def __str__(self):
        return 'played ' + self.song.displayname() + ' with ' + str(self.votes) + ' votes'

class Setting(models.Model):
    key = models.CharField(max_length=200, unique=True)
    value = models.CharField(max_length=200)
    def __str__(self):
        return self.key + ': ' + ('None' if self.value is None else self.value)

class Pad(models.Model):
    version = models.IntegerField(default=0)
    content = models.CharField(max_length=100000)
    def __str__(self):
        return '{' + str(self.version) + '}: ' + self.content[:20] + '...'
