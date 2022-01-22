"""This module contains the syncsongmetadata command."""
from django.core.management.base import BaseCommand

from core.musiq import song_utils


class Command(BaseCommand):
    """Defines the syncsongmetadata command."""

    help = (
        "Goes through every archived song and syncs its metadata from the file system."
    )

    def handle(self, *args, **options):
        from core.models import ArchivedSong
        from core.musiq.song_provider import SongProvider

        for song in ArchivedSong.objects.all():
            try:
                provider = SongProvider.create(external_url=song.url)
            except NotImplementedError:
                # For this song a provider is necessary that is not available
                # e.g. the song was played before, but the provider was disabled
                continue
            cached = provider.check_cached()
            if cached:
                # sync the metadata in the database with the file system
                # _get_path is defined for localdrive and youtube,
                # the only two providers that may be cached
                from core.musiq.local import LocalSongProvider
                from core.musiq.youtube import YoutubeSongProvider

                assert isinstance(provider, (YoutubeSongProvider, LocalSongProvider))
                metadata = song_utils.get_metadata(provider.get_path())
                song.artist = metadata["artist"]
                song.title = metadata["title"]
                song.duration = metadata["duration"]
                song.cached = True
            else:
                # keep old data but store that the song is not cached
                song.cached = False
            song.save()
