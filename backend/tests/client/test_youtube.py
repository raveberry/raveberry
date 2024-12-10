import os
import sys
from typing import Callable, Optional

import yt_dlp
from django.conf import settings
from django.urls import reverse
from unittest import skip, skipIf

from core.musiq.youtube import Youtube
from core.settings import storage
from tests.music_test import MusicTest


class YoutubeDLLogger:
    def __init__(self, test: MusicTest):
        self.test = test

    @classmethod
    def debug(cls, msg: str) -> None:
        pass

    @classmethod
    def warning(cls, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        self.test.tearDown()
        self.test.skipTest(msg)


class YoutubeTests(MusicTest):
    def setUp(self) -> None:
        super().setUp()
        try:
            # try to find out whether youtube is happy with us this time
            # send a request and skip the test if there is an error
            ydl_opts = Youtube.get_ydl_opts()
            ydl_opts["logger"] = YoutubeDLLogger(self)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.info_dict = ydl.download(
                    ["https://www.youtube.com/watch?v=ZvD8QSO7NPw"]
                )
        except (yt_dlp.utils.ExtractorError, yt_dlp.utils.DownloadError) as error:
            super().tearDown()
            self.skipTest(
                f"Error when interacting with youtube, skipping test: {error}"
            )

        # reduce the number for youtube playlists
        storage.put("max_playlist_items", 3)

        # if we want to make sure that the songs can be downloaded,
        # we could delete all songs in the test_cache folder
        # if os.path.split(os.path.dirname(settings.SONGS_CACHE_DIR))[1] == "test_cache":
        #    for member in os.listdir(settings.SONGS_CACHE_DIR):
        #        member_path = os.path.join(settings.SONGS_CACHE_DIR, member)
        #        if os.path.isfile(member_path):
        #            os.remove(member_path)

    def _poll_musiq_state(
        self, break_condition: Callable[[dict], bool], timeout: float = 1
    ) -> dict:
        """Wrap the poll method of the super class to skip tests if Youtube doesn't play along."""
        try:
            return super()._poll_musiq_state(break_condition, timeout=timeout)
        except AssertionError:
            with open(
                os.path.join(settings.BASE_DIR, "logs/info.log"), encoding="utf-8"
            ) as log:
                line = None
                for line in log:
                    pass
                last_line = line
                if (
                    "ERROR: No video formats found" in last_line
                    or "ERROR: Unable to download webpage" in last_line
                ):
                    self.skipTest("Youtube provided no video formats")
            raise

    def _post_request(
        self, url: str, query: Optional[str] = None, playlist: bool = False
    ) -> None:
        if not query:
            response = self.client.post(reverse(url))
        else:
            response = self.client.post(
                reverse(url),
                {
                    "query": query,
                    "playlist": "true" if playlist else "false",
                    "platform": "youtube",
                },
            )
        if (
            response.status_code == 400
            and b"429" in response.content
            or b"403" in response.content
        ):
            self.skipTest("This IP sent too many requests to Youtube.")

    def test_query(self) -> None:
        self._post_request("request-music", "Myuu Disintegrating")
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["externalUrl"], "https://www.youtube.com/watch?v=piFJVwr1YYA"
        )
        self.assertIn("Disintegrating", current_song["title"])
        self.assertAlmostEqual(current_song["duration"], 284, delta=1)

    def test_url(self):
        self._post_request(
            "request-music", "https://www.youtube.com/watch?v=ZvD8QSO7NPw"
        )
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["externalUrl"], "https://www.youtube.com/watch?v=ZvD8QSO7NPw"
        )
        self.assertIn("Collapse", current_song["title"])
        self.assertAlmostEqual(current_song["duration"], 200, delta=1)

    def test_playlist_url(self):
        self._post_request(
            "request-music",
            "https://www.youtube.com/playlist?list=PLt4ZkJ3lYmFXG33Jk4BWaV4y0vypFCGtm",
            playlist=True,
        )
        state = self._poll_musiq_state(
            lambda state: state["musiq"]["currentSong"]
            and len(state["musiq"]["songQueue"]) == 2
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=60,
        )
        expected_playlist = [
            "https://www.youtube.com/watch?v=ZvD8QSO7NPw",
            "https://www.youtube.com/watch?v=piFJVwr1YYA",
            "https://www.youtube.com/watch?v=Dz-tOLvN4C0",
        ]
        # The first song that is downloaded will be played.
        # This is not necessarily the first one in the playlist.
        self.assertIn(state["musiq"]["currentSong"]["externalUrl"], expected_playlist)
        expected_playlist.remove(state["musiq"]["currentSong"]["externalUrl"])
        actual_playlist = [
            state["musiq"]["songQueue"][0]["externalUrl"],
            state["musiq"]["songQueue"][1]["externalUrl"],
        ]
        # make sure the remaining songs are in expected order
        self.assertEqual(actual_playlist, expected_playlist)

    @skip("Albums not yet supported")
    def test_playlist_query(self):
        self._post_request(
            "request-music",
            '"Myuu" "Sad Piano Music"',
            playlist=True,
        )
        state = self._poll_musiq_state(
            lambda state: state["musiq"]["currentSong"]
            and len(state["musiq"]["songQueue"]) == 2
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=60,
        )
        expected_playlist = [
            "https://www.youtube.com/watch?v=ZvD8QSO7NPw",
            "https://www.youtube.com/watch?v=piFJVwr1YYA",
            "https://www.youtube.com/watch?v=Dz-tOLvN4C0",
        ]
        # The first song that is downloaded will be played.
        # This is not necessarily the first one in the playlist.
        self.assertIn(state["musiq"]["currentSong"]["externalUrl"], expected_playlist)
        expected_playlist.remove(state["musiq"]["currentSong"]["externalUrl"])
        actual_playlist = [
            state["musiq"]["songQueue"][0]["externalUrl"],
            state["musiq"]["songQueue"][1]["externalUrl"],
        ]
        # make sure the remaining songs are in expected order
        self.assertEqual(actual_playlist, expected_playlist)

    @skipIf(
        not sys.argv[-1].endswith("test_autoplay"),
        "This test can only be run individually.",
    )
    def test_autoplay(self) -> None:
        self._post_request(
            "request-music", "https://www.youtube.com/watch?v=ZvD8QSO7NPw"
        )
        self._poll_current_song()
        self.client.post(reverse("set-autoplay"), {"value": "true"})
        # make sure a song was downloaded into the queue
        # sometimes this fails due to long songs taking too long to download
        state = self._poll_musiq_state(
            lambda state: len(state["musiq"]["songQueue"]) == 1
            and state["musiq"]["songQueue"][0]["internalUrl"],
            timeout=20,
        )
        old_id = state["musiq"]["songQueue"][0]["id"]

        self.client.post(reverse("skip"))
        # make sure another song is enqueued
        self._wait_for_new_song(old_id)

    def test_radio(self) -> None:
        self._post_request(
            "request-music", "https://www.youtube.com/watch?v=ZvD8QSO7NPw"
        )
        self._poll_current_song()
        self._post_request("request-radio")
        # ensure that enough songs are enqueued
        self._poll_musiq_state(
            lambda state: len(state["musiq"]["songQueue"]) == 3
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=60,
        )
