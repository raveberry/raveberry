"""This module handles all settings related to the local library."""

from __future__ import annotations

import logging
import os
import time
from typing import Tuple, List

from django.conf import settings as conf
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from mutagen import MutagenError

from core import redis
from core.models import ArchivedPlaylist, ArchivedSong, PlaylistEntry
from core.musiq import song_utils
from core.settings import settings
from core.settings.settings import control
from core.tasks import app

UPDATE_FREQUENCY = 0.5


def get_library_path() -> str:
    """Returns the absolute path of the local library."""
    return os.path.abspath(os.path.join(conf.SONGS_CACHE_DIR, "local_library"))


@control
def list_subdirectories(request: WSGIRequest) -> HttpResponse:
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


def _set_scan_progress(scan_progress: str) -> None:
    redis.put("library_scan_progress", scan_progress)
    settings.update_state()


@control
def scan_library(request: WSGIRequest) -> HttpResponse:
    """Scan the folder at the given path and add all its sound files to the database."""
    library_path = request.POST.get("library_path")
    if library_path is None:
        return HttpResponseBadRequest("library path was not supplied.")

    if not os.path.isdir(library_path):
        return HttpResponseBadRequest("not a directory")
    library_path = os.path.abspath(library_path)

    _set_scan_progress("0 / 0 / 0")

    _scan_library.delay(library_path)

    return HttpResponse(f"started scanning in {library_path}. This could take a while")


def _count_files(library_path: str) -> int:
    last_update = time.time()
    filecount = 0
    for dirpath, _, filenames in os.walk(library_path):
        now = time.time()
        if now - last_update > UPDATE_FREQUENCY:
            last_update = now
            _set_scan_progress(f"{filecount} / 0 / 0")
        if os.path.abspath(dirpath) == os.path.abspath(conf.SONGS_CACHE_DIR):
            # do not add files handled by raveberry as local files
            continue
        filecount += len(filenames)
    _set_scan_progress(f"{filecount} / 0 / 0")
    return filecount


def _scan_files(library_path: str, filecount: int) -> Tuple[int, int]:
    last_update = time.time()
    files_scanned = 0
    files_added = 0
    for dirpath, _, filenames in os.walk(library_path):
        if os.path.abspath(dirpath) == os.path.abspath(conf.SONGS_CACHE_DIR):
            # do not add files handled by raveberry as local files
            continue
        now = time.time()
        if now - last_update > UPDATE_FREQUENCY:
            last_update = now
            _set_scan_progress(f"{filecount} / {files_scanned} / {files_added}")
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
                        duration=metadata["duration"],
                        counter=0,
                        cached=metadata["cached"],
                    )
    return files_scanned, files_added


@app.task
def _scan_library(library_path: str) -> None:
    library_link = os.path.join(conf.SONGS_CACHE_DIR, "local_library")
    try:
        os.remove(library_link)
    except FileNotFoundError:
        pass
    os.symlink(library_path, library_link)

    filecount = _count_files(library_path)

    logging.info("started scanning in %s", library_path)

    files_scanned, files_added = _scan_files(library_path, filecount)

    assert files_scanned == filecount
    _set_scan_progress(f"{filecount} / {files_scanned} / {files_added}")

    logging.info("done scanning in %s", library_path)


@control
def create_playlists(_request: WSGIRequest) -> HttpResponse:
    """Create a playlist for every folder in the library."""
    library_link = os.path.join(conf.SONGS_CACHE_DIR, "local_library")
    if not os.path.islink(library_link):
        return HttpResponseBadRequest("No library set")

    _set_scan_progress("0 / 0 / 0")

    _create_playlists.delay()

    return HttpResponse("started creating playlists. This could take a while")


@app.task
def _create_playlists() -> None:
    local_files = ArchivedSong.objects.filter(url__startswith="local_library").count()

    library_link = os.path.join(conf.SONGS_CACHE_DIR, "local_library")
    library_path = os.path.abspath(library_link)

    logging.info("started creating playlists in %s", library_path)

    _set_scan_progress(f"{local_files} / 0 / 0")

    scan_start = time.time()
    last_update = scan_start
    files_processed = 0
    files_added = 0

    def _scan_folder(dirpath: str) -> List[str]:
        nonlocal last_update, files_processed, files_added
        now = time.time()
        if now - last_update > UPDATE_FREQUENCY:
            last_update = now
            _set_scan_progress(f"{local_files} / {files_processed} / {files_added}")

        song_urls = []
        # unfortunately there is no way to access track numbers across different file types
        # so we have to add songs to playlists alphabetically
        for filename in sorted(os.listdir(dirpath)):
            path = os.path.join(dirpath, filename)

            if os.path.isdir(path):
                song_urls.extend(_scan_folder(path))
                continue

            library_relative_path = path[len(library_path) + 1 :]
            external_url = os.path.join("local_library", library_relative_path)
            if ArchivedSong.objects.filter(url=external_url).exists():
                files_processed += 1
                song_urls.append(external_url)

        if not song_urls:
            return []

        playlist_id = os.path.join("local_library", dirpath[len(library_path) + 1 :])
        playlist_title = os.path.split(dirpath)[1]
        playlist, created = ArchivedPlaylist.objects.get_or_create(
            list_id=playlist_id, title=playlist_title, counter=0
        )
        if not created:
            # this playlist already exists, skip
            return song_urls

        song_index = 0
        for external_url in song_urls:
            PlaylistEntry.objects.create(
                playlist=playlist, index=song_index, url=external_url
            )
            files_added += 1
            song_index += 1

        return song_urls

    _scan_folder(library_path)

    _set_scan_progress(f"{local_files} / {files_processed} / {files_added}")
