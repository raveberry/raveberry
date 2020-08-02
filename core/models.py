"""Contains all database models."""

from django.db import models
from django.db.models import QuerySet

import core.musiq.song_queue
import core.musiq.song_utils as song_utils


# Create your models here.
class Tag(models.Model):
    """Stores hashtags."""

    text = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.text


class Counter(models.Model):
    """Stores the visitors counter. Only has one elment."""

    value = models.IntegerField()

    def __str__(self) -> str:
        return str(self.value)


class ArchivedSong(models.Model):
    """Stores an archived song.
    url identifies the song uniquely in the database and on the internet (if applicable)."""

    url = models.CharField(max_length=2000, unique=True)
    artist = models.CharField(max_length=1000)
    title = models.CharField(max_length=1000)
    counter = models.IntegerField()

    def __str__(self) -> str:
        return self.title + " (" + self.url + "): " + str(self.counter)

    def displayname(self) -> str:
        """Formats the song using the utility method."""
        return song_utils.displayname(self.artist, self.title)


class ArchivedPlaylist(models.Model):
    """Stores an archived playlist.
    url identifies the playlist uniquely in the database and on the internet (if applicable)."""

    id: int
    entries: QuerySet
    list_id = models.CharField(max_length=2000)
    title = models.CharField(max_length=1000)
    created = models.DateTimeField(auto_now_add=True)
    counter = models.IntegerField()

    def __str__(self) -> str:
        return self.title + ": " + str(self.counter)


class PlaylistEntry(models.Model):
    """Stores an entry to a playlist. Connects ArchivedSong and ArchivedPlaylist."""

    playlist = models.ForeignKey(
        "ArchivedPlaylist", on_delete=models.CASCADE, related_name="entries"
    )
    index = models.IntegerField()
    url = models.CharField(max_length=2000)

    def __str__(self) -> str:
        return self.playlist.title + "[" + str(self.index) + "]: " + self.url

    class Meta:
        ordering = ["playlist", "index"]


class ArchivedQuery(models.Model):
    """Stores the queries from the musiq page and the ArchivedSong it lead to."""

    song = models.ForeignKey(
        "ArchivedSong", on_delete=models.CASCADE, related_name="queries"
    )
    query = models.CharField(max_length=1000)

    def __str__(self) -> str:
        return self.query


class ArchivedPlaylistQuery(models.Model):
    """Stores the queries from the musiq page and the ArchivedPlaylist it lead to."""

    playlist = models.ForeignKey(
        "ArchivedPlaylist", on_delete=models.CASCADE, related_name="queries"
    )
    query = models.CharField(max_length=1000)

    def __str__(self) -> str:
        return self.query


class QueuedSong(models.Model):
    """Stores a song in the song queue so the queue is not lost on server restart."""

    id: int
    index = models.IntegerField()
    manually_requested = models.BooleanField()
    votes = models.IntegerField(default=0)
    # A placeholder has an empty internal url to prevent migrations
    # With the next mandatory migration, this should probably be changed to None,
    # adding null=True to this field
    internal_url = models.CharField(max_length=2000)
    external_url = models.CharField(max_length=2000, blank=True)
    artist = models.CharField(max_length=1000)
    title = models.CharField(max_length=1000)
    duration = models.IntegerField()
    objects = core.musiq.song_queue.SongQueue()

    def __str__(self) -> str:
        return str(self.index) + ": " + self.title + " (" + self.internal_url + ")"

    def displayname(self) -> str:
        """Formats the song using the utility method."""
        return song_utils.displayname(self.artist, self.title)

    class Meta:
        ordering = ["index"]


class CurrentSong(models.Model):
    """Stores the currently playing song. Only has one element."""

    queue_key = models.IntegerField()
    manually_requested = models.BooleanField()
    votes = models.IntegerField()
    internal_url = models.CharField(max_length=2000)
    external_url = models.CharField(max_length=2000, blank=True)
    artist = models.CharField(max_length=1000)
    title = models.CharField(max_length=1000)
    duration = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title + " (" + self.internal_url + ")"

    def displayname(self) -> str:
        """Formats the song using the utility method."""
        return song_utils.displayname(self.artist, self.title)


class RequestLog(models.Model):
    """Stores the request of a client and its result."""

    created = models.DateTimeField(auto_now_add=True)
    song = models.ForeignKey(
        "ArchivedSong", on_delete=models.SET_NULL, blank=True, null=True
    )
    playlist = models.ForeignKey(
        "ArchivedPlaylist", on_delete=models.SET_NULL, blank=True, null=True
    )
    address = models.CharField(max_length=50)

    def item_displayname(self) -> str:
        """Returns the displayname of the song or the title of the playlist"""
        if self.song is not None:
            return self.song.displayname()
        if self.playlist is not None:
            return self.playlist.title
        return "Unknown"

    def __str__(self) -> str:
        if self.song is not None:
            return self.address + ": " + self.song.displayname()
        if self.playlist is not None:
            return self.address + ": " + self.playlist.title
        return self.address + ": <None>"


class PlayLog(models.Model):
    """Stores the log of a played song."""

    created = models.DateTimeField(auto_now_add=True)
    song = models.ForeignKey(
        "ArchivedSong", on_delete=models.SET_NULL, blank=True, null=True
    )
    manually_requested = models.BooleanField()
    votes = models.IntegerField(null=True)

    def song_displayname(self) -> str:
        """Returns the displayname of the song (if present)"""
        if not self.song:
            return "Unknown"
        return self.song.displayname()

    def __str__(self) -> str:
        return (
            "played " + self.song_displayname() + " with " + str(self.votes) + " votes"
        )


class Setting(models.Model):
    """key value storage for persistent settings."""

    key = models.CharField(max_length=200, unique=True)
    value = models.CharField(max_length=200)

    def __str__(self) -> str:
        return self.key + ": " + ("None" if self.value is None else self.value)
