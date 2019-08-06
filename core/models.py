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

class ArchivedQuery(models.Model):
    song = models.ForeignKey('ArchivedSong', on_delete=models.CASCADE, related_name='queries')
    query = models.CharField(max_length=1000)
    def __str__(self):
        return self.query

class QueuedSong(models.Model):
    index = models.IntegerField()
    votes = models.IntegerField(default=0)
    url = models.CharField(max_length=200)
    artist = models.CharField(max_length=1000)
    title = models.CharField(max_length=1000)
    duration = models.CharField(max_length=20)
    objects = core.musiq.song_queue.SongQueue()
    def __str__(self):
        return str(self.index) + ': ' + self.title + ' (' + self.url + ')'
    def displayname(self):
        return song_utils.displayname(self.artist, self.title)
    class Meta:
       ordering = ['index']

class CurrentSong(models.Model):
    queue_key = models.IntegerField()
    votes = models.IntegerField()
    url = models.CharField(max_length=200)
    artist = models.CharField(max_length=1000)
    title = models.CharField(max_length=1000)
    duration = models.CharField(max_length=20)
    location = models.CharField(max_length=1000)
    created = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.title + ' (' + self.url + ')'
    def displayname(self):
        return song_utils.displayname(self.artist, self.title)

class RequestLog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    song = models.ForeignKey('ArchivedSong', on_delete=models.SET_NULL, blank=True, null=True)
    address = models.CharField(max_length=50)
    def __str__(self):
        return self.address + ': ' + self.song.displayname()

class PlayLog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    song = models.ForeignKey('ArchivedSong', on_delete=models.SET_NULL, blank=True, null=True)
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
