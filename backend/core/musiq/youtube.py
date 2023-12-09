"""This module contains all Youtube related code."""
# We need to access yt-dlp's internal methods for some features
# pylint: disable=protected-access

from __future__ import annotations

import errno
import logging
import os
import pickle
import subprocess
import urllib.parse
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, cast
from urllib.parse import parse_qs, urlparse

import requests
import yt_dlp
import ytmusicapi
from django.conf import settings
from django.http.response import HttpResponse

from core.musiq import musiq, song_utils
from core.musiq.playlist_provider import PlaylistProvider
from core.musiq.song_provider import SongProvider
from core.settings import storage


@contextmanager
def youtube_session() -> Iterator[requests.Session]:
    """This context opens a requests session and loads the youtube cookies file."""

    cookies_path = os.path.join(settings.BASE_DIR, "config/youtube_cookies.pickle")
    session = requests.session()
    # Have yt-dlp deal with consent cookies etc to setup a valid session
    extractor = yt_dlp.extractor.youtube.YoutubeIE()
    extractor._downloader = yt_dlp.YoutubeDL()
    extractor.initialize()
    session.cookies.update(extractor._downloader.cookiejar)

    try:
        if os.path.getsize(cookies_path) > 0:
            with open(cookies_path, "rb") as cookies_file:
                session.cookies.update(pickle.load(cookies_file))
    except FileNotFoundError:
        pass

    headers = {"User-Agent": yt_dlp.utils.random_user_agent()}
    session.headers.update(headers)
    yield session

    with open(cookies_path, "wb") as cookies_file:
        pickle.dump(session.cookies, cookies_file)


class YoutubeDLLogger:
    """This logger class is used to log process of yt-dlp downloads."""

    @classmethod
    def debug(cls, msg: str) -> None:
        """This method is called if yt-dlp does debug level logging."""
        logging.debug(msg)

    @classmethod
    def warning(cls, msg: str) -> None:
        """This method is called if yt-dlp does warning level logging."""
        logging.debug(msg)

    @classmethod
    def error(cls, msg: str) -> None:
        """This method is called if yt-dlp does error level logging."""
        logging.error(msg)


class Youtube:
    """This class contains code for both the song and playlist provider"""

    used_info_dict_keys = {"id", "filesize", "url", "_type", "title", "entries"}

    @staticmethod
    def get_ydl_opts() -> Dict[str, Any]:
        """This method returns a dictionary containing sensible defaults for yt-dlp options.
        It is roughly equivalent to the following command:
        yt-dlp --format bestaudio[ext=m4a]/best[ext=m4a] --output '%(id)s.%(ext)s' \
            --no-playlist --no-cache-dir --write-thumbnail --default-search auto \
            --add-metadata --embed-thumbnail
        """
        postprocessors = [
            {"key": "FFmpegMetadata"},
            {
                "key": "EmbedThumbnail",
                # overwrite any thumbnails already present
                "already_have_thumbnail": True,
            },
        ]
        return {
            "format": "bestaudio[ext=m4a]/best[ext=m4a]",
            "outtmpl": os.path.join(settings.SONGS_CACHE_DIR, "%(id)s.%(ext)s"),
            "noplaylist": True,
            "cachedir": False,
            "no_color": True,
            "writethumbnail": True,
            "default_search": "auto",
            "postprocessors": postprocessors,
            "logger": YoutubeDLLogger(),
        }

    @staticmethod
    def get_search_suggestions(query: str) -> List[str]:
        """Returns a list of suggestions for the given query from Youtube."""
        with youtube_session() as session:
            params = {
                "client": "youtube",
                "q": query[:100],  # queries longer than 100 characters are not accepted
                "xhr": "t",  # this makes the response be a json file
            }
            response = session.get(
                "https://clients1.google.com/complete/search", params=params
            )
        suggestions = ytmusicapi.YTMusic().get_search_suggestions(query)
        try:
            if suggestions[0] == query:
                suggestions = suggestions[1:]
        except IndexError:
            return []
        return suggestions


class YoutubeSongProvider(SongProvider, Youtube):
    """This class handles songs from Youtube."""

    @staticmethod
    def get_id_from_external_url(url: str) -> str:
        return parse_qs(urlparse(url).query)["v"][0]

    def __init__(self, query: Optional[str], key: Optional[int]) -> None:
        self.type = "youtube"
        super().__init__(query, key)
        self.info_dict: Dict[str, Any] = {}

    def check_cached(self) -> bool:
        if not self.id:
            # id could not be extracted from query, needs to be serched
            return False
        if storage.get("output") == "client":
            # youtube streaming links need to be fetched each time the song is requested
            return False
        return os.path.isfile(self.get_path())

    def check_available(self) -> bool:
        info_dict = None

        def extract_info(id):
            nonlocal info_dict
            try:
                with yt_dlp.YoutubeDL(Youtube.get_ydl_opts()) as ydl:
                    info_dict = ydl.extract_info(id, download=False)
                    return True
            except (yt_dlp.utils.ExtractorError, yt_dlp.utils.DownloadError) as error:
                logging.warning("error during availability check for %s:", id)
                logging.warning(error)
            return False

        if self.id:
            # do not search if an id is already present
            extract_info(self.id)
        else:
            # do not filter to only receive "song" results, because we would skip the top result
            results = ytmusicapi.YTMusic().search(self.query)
            for result in results:
                if result["resultType"] not in ("video", "song"):
                    continue
                if song_utils.is_forbidden(result["title"]):
                    continue
                if extract_info(result["videoId"]):
                    break

        if not info_dict:
            self.error = "No songs found"
            return False

        self.id = info_dict["id"]

        return self.check_not_too_large(info_dict["filesize"])

    def _download(self) -> bool:
        download_error = None
        location = None

        try:
            with yt_dlp.YoutubeDL(Youtube.get_ydl_opts()) as ydl:
                ydl.download([self.get_external_url()])

            location = self.get_path()
            base = os.path.splitext(location)[0]
            thumbnail = base + ".jpg"
            try:
                os.remove(thumbnail)
            except FileNotFoundError:
                logging.info("tried to delete %s but does not exist", thumbnail)

            try:
                # tag the file with replaygain to perform volume normalization
                subprocess.call(
                    ["rganalysis", location],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError as error:
                if error.errno == errno.ENOENT:
                    pass  # the rganalysis package was not found. Skip normalization
                else:
                    raise

        except yt_dlp.utils.DownloadError as error:
            download_error = error

        if download_error is not None or location is None:
            logging.error("accessible video could not be downloaded: %s", self.id)
            logging.error("location: %s", location)
            logging.error(download_error)
            return False
        return True

    def make_available(self) -> bool:
        if os.path.isfile(self.get_path()):
            # don't download the file if it is already cached
            return True
        musiq.update_state()
        return self._download()

    def get_path(self) -> str:
        """Return the path in the local filesystem to the cached sound file of this song."""
        if not self.id:
            raise ValueError()
        return song_utils.get_path(self.id + ".m4a")

    def get_internal_url(self) -> str:
        return "file://" + urllib.parse.quote(self.get_path())

    def get_external_url(self) -> str:
        if not self.id:
            raise ValueError()
        return "https://www.youtube.com/watch?v=" + self.id

    def gather_metadata(self) -> bool:
        self.metadata = self.get_local_metadata(self.get_path())
        return True

    def get_suggestion(self) -> str:
        result = ytmusicapi.YTMusic().get_watch_playlist(self.id, limit=2)
        # the first entry usually is the song itself -> use the second one
        suggested_id = result["tracks"][1]["videoId"]
        return "https://www.youtube.com/watch?v=" + suggested_id

    def request_radio(self, session_key: str) -> HttpResponse:
        if not self.id:
            raise ValueError()

        result = ytmusicapi.YTMusic().get_watch_playlist(
            self.id, limit=storage.get("max_playlist_items"), radio=True
        )
        radio_id = result["playlistId"]

        provider = YoutubePlaylistProvider("", None)
        provider.id = radio_id
        provider.title = radio_id
        for entry in result["tracks"]:
            provider.urls.append("https://www.youtube.com/watch?v=" + entry["videoId"])
        provider.request("", archive=False, manually_requested=False)
        return HttpResponse("queueing radio (might take some time)")


class YoutubePlaylistProvider(PlaylistProvider, Youtube):
    """This class handles Youtube Playlists."""

    @staticmethod
    def get_id_from_external_url(url: str) -> Optional[str]:
        try:
            list_id = parse_qs(urlparse(url).query)["list"][0]
        except KeyError:
            return None
        return list_id

    def __init__(self, query: Optional[str], key: Optional[int]) -> None:
        self.type = "youtube"
        super().__init__(query, key)

    def is_radio(self) -> bool:
        if not self.id:
            raise ValueError()
        return self.id.startswith("RD")

    def search_id(self) -> Optional[str]:
        results = ytmusicapi.YTMusic().search(self.query)

        for result in results:
            if result["resultType"] not in (
                "playlist",
                "community_playlist",
                "featured_playlist",
            ):
                continue
            if "browseId" not in result or not result["browseId"]:
                continue
            # remove the preceding "VL" from the playlist id
            list_id = result["browseId"][2:]
            return list_id

    def fetch_metadata(self) -> bool:
        assert self.id

        # radio playlists are prefilled when requesting them
        if self.title and self.urls:
            return True

        try:
            result = ytmusicapi.YTMusic().get_playlist(self.id)
        except Exception as e:
            # query was not a playlist url -> search for the query
            assert False

        assert self.id == result["id"]
        self.title = result["title"]
        for entry in result["tracks"]:
            if "videoId" not in entry or not entry["videoId"]:
                continue
            self.urls.append("https://www.youtube.com/watch?v=" + entry["videoId"])
        assert self.key is None

        return True
