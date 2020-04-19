"""This module provides some utility functions concerning songs."""

import os

import mutagen.easymp4

from main import settings


def get_path(basename):
    """Returns the absolute path for a basename of a file in the cache directory."""
    path = os.path.join(settings.SONGS_CACHE_DIR, basename)
    path = path.replace("~", os.environ["HOME"])
    path = os.path.abspath(path)
    return path


def determine_playlist_type(archived_playlist):
    """Uses the url of the first song in the playlist
    to determine the platform where the playlist is from."""
    first_song_url = archived_playlist.entries.first().url
    if first_song_url.startswith("local_library/"):
        return "local"
    if first_song_url.startswith("https://www.youtube.com/"):
        return "youtube"
    if first_song_url.startswith("https://open.spotify.com/"):
        return "spotify"
    return None


def format_seconds(seconds):
    """Takes seconds and formats them as [hh:]mm:ss."""
    hours, seconds = seconds // 3600, seconds % 3600
    minutes, seconds = seconds // 60, seconds % 60

    formatted = ""
    if hours > 0:
        formatted += "{:02d}:".format(int(hours))
    formatted += "{0:02d}:{1:02d}".format(int(minutes), int(seconds))
    return formatted


def displayname(artist, title):
    """Formats the given artist and title as a presentable display name."""
    if artist == "":
        return title
    return artist + " – " + title


def get_metadata(path):
    """gathers the metadata for the song at the given location.
    'title' and 'duration' is read from tags, the 'url' is built from the location"""

    parsed = mutagen.File(path, easy=True)
    if parsed is None:
        raise ValueError
    metadata = dict()

    if parsed.tags is not None:
        if "artist" in parsed.tags:
            metadata["artist"] = parsed.tags["artist"][0]
        if "title" in parsed.tags:
            metadata["title"] = parsed.tags["title"][0]
    if "artist" not in metadata:
        metadata["artist"] = ""
    if "title" not in metadata:
        metadata["title"] = os.path.split(path)[1]
    if parsed.info is not None and parsed.info.length is not None:
        metadata["duration"] = parsed.info.length
    else:
        metadata["duration"] = -1

    return metadata
