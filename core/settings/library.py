"""This module handles all settings related to the local library."""

from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from mutagen import MutagenError

import core.musiq.song_utils as song_utils
from core.models import ArchivedSong, ArchivedPlaylist, PlaylistEntry
from core.settings.settings import Settings
from core.util import background_thread

if TYPE_CHECKING:
    from core.base import Base


class Library:
    """This class is responsible for handling settings changes related to the local library."""

    def __init__(self, base: "Base"):
        self.base = base
        self.scan_progress = "0 / 0 / 0"

    @staticmethod
    def get_library_path() -> str:
        return os.path.abspath(os.path.join(settings.SONGS_CACHE_DIR, "local_library"))

    @Settings.option
    def list_subdirectories(self, request: WSGIRequest) -> HttpResponse:
        """Returns a list of all subdirectories for the given path."""
        path = request.GET.get("path")
        if path is None:
            return HttpResponseBadRequest("path was not supplied.")
        basedir, subdirpart = os.path.split(path)
        if path == "":
            suggestions = ["/"]
        elif os.path.isdir(basedir):
            suggestions = [
                os.path.join(basedir, subdir + "/")
                for subdir in next(os.walk(basedir))[1]
                if subdir.lower().startswith(subdirpart.lower())
            ]
            suggestions.sort()
        else:
            suggestions = ["not a valid directory"]
        if not suggestions:
            suggestions = ["not a valid directory"]
        return JsonResponse(suggestions, safe=False)

    @Settings.option
    def scan_library(self, request: WSGIRequest) -> HttpResponse:
        """Scan the folder at the given path and add all its sound files to the database."""
        library_path = request.POST.get("library_path")
        if library_path is None:
            return HttpResponseBadRequest("library path was not supplied.")

        if not os.path.isdir(library_path):
            return HttpResponseBadRequest("not a directory")
        library_path = os.path.abspath(library_path)

        self.scan_progress = "0 / 0 / 0"
        self.base.settings.update_state()

        self._scan_library(library_path)

        return HttpResponse(
            f"started scanning in {library_path}. This could take a while"
        )

    @background_thread
    def _scan_library(self, library_path: str) -> None:
        scan_start = time.time()
        last_update = scan_start
        update_frequency = 0.5
        filecount = 0
        for (dirpath, _, filenames) in os.walk(library_path):
            now = time.time()
            if now - last_update > update_frequency:
                last_update = now
                self.scan_progress = f"{filecount} / 0 / 0"
                self.base.settings.update_state()
            if os.path.abspath(dirpath) == os.path.abspath(settings.SONGS_CACHE_DIR):
                # do not add files handled by raveberry as local files
                continue
            filecount += len(filenames)

        library_link = os.path.join(settings.SONGS_CACHE_DIR, "local_library")
        try:
            os.remove(library_link)
        except FileNotFoundError:
            pass
        os.symlink(library_path, library_link)

        logging.info("started scanning in %s", library_path)

        self.scan_progress = f"{filecount} / 0 / 0"
        self.base.settings.update_state()

        files_scanned = 0
        files_added = 0
        for (dirpath, _, filenames) in os.walk(library_path):
            if os.path.abspath(dirpath) == os.path.abspath(settings.SONGS_CACHE_DIR):
                # do not add files handled by raveberry as local files
                continue
            now = time.time()
            if now - last_update > update_frequency:
                last_update = now
                self.scan_progress = f"{filecount} / {files_scanned} / {files_added}"
                self.base.settings.update_state()
            for filename in filenames:
                files_scanned += 1
                path = os.path.join(dirpath, filename)
                try:
                    metadata = song_utils.get_metadata(path)
                except (ValueError, MutagenError):
                    # the given file could not be parsed and will not be added to the database
                    pass
                else:
                    library_relative_path = path[len(library_path) + 1 :]
                    external_url = os.path.join("local_library", library_relative_path)
                    if not ArchivedSong.objects.filter(url=external_url).exists():
                        files_added += 1
                        ArchivedSong.objects.create(
                            url=external_url,
                            artist=metadata["artist"],
                            title=metadata["title"],
                            counter=0,
                        )

        assert files_scanned == filecount
        self.scan_progress = f"{filecount} / {files_scanned} / {files_added}"
        self.base.settings.update_state()

        logging.info("done scanning in %s", library_path)

    @Settings.option
    def create_playlists(self, _request: WSGIRequest) -> HttpResponse:
        """Create a playlist for every folder in the library."""
        library_link = os.path.join(settings.SONGS_CACHE_DIR, "local_library")
        if not os.path.islink(library_link):
            return HttpResponseBadRequest("No library set")

        self.scan_progress = f"0 / 0 / 0"
        self.base.settings.update_state()

        self._create_playlists()

        return HttpResponse(f"started creating playlists. This could take a while")

    @background_thread
    def _create_playlists(self) -> None:
        local_files = ArchivedSong.objects.filter(
            url__startswith="local_library"
        ).count()

        library_link = os.path.join(settings.SONGS_CACHE_DIR, "local_library")
        library_path = os.path.abspath(library_link)

        logging.info("started creating playlists in %s", library_path)

        self.scan_progress = f"{local_files} / 0 / 0"
        self.base.settings.update_state()

        scan_start = time.time()
        last_update = scan_start
        update_frequency = 0.5
        files_processed = 0
        files_added = 0
        for (dirpath, _, filenames) in os.walk(library_path):
            now = time.time()
            if now - last_update > update_frequency:
                last_update = now
                self.scan_progress = (
                    f"{local_files} / {files_processed} / {files_added}"
                )
                self.base.settings.update_state()

            song_urls = []
            # unfortunately there is no way to access track numbers accross different file types
            # so we have to add songs to playlists alphabetically
            for filename in sorted(filenames):
                path = os.path.join(dirpath, filename)
                library_relative_path = path[len(library_path) + 1 :]
                external_url = os.path.join("local_library", library_relative_path)
                if ArchivedSong.objects.filter(url=external_url).exists():
                    files_processed += 1
                    song_urls.append(external_url)

            if not song_urls:
                continue

            playlist_id = os.path.join(
                "local_library", dirpath[len(library_path) + 1 :]
            )
            playlist_title = os.path.split(dirpath)[1]
            playlist, created = ArchivedPlaylist.objects.get_or_create(
                list_id=playlist_id, title=playlist_title, counter=0
            )
            if not created:
                # this playlist already exists, skip
                continue

            song_index = 0
            for external_url in song_urls:
                PlaylistEntry.objects.create(
                    playlist=playlist, index=song_index, url=external_url
                )
                files_added += 1
                song_index += 1

        self.scan_progress = f"{local_files} / {files_processed} / {files_added}"
        self.base.settings.update_state()
