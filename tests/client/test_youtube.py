import os

import youtube_dl
from django.conf import settings
from django.urls import reverse

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
        print(msg)
        self.test.skipTest(msg)


class YoutubeTests(MusicTest):
    def setUp(self):
        super().setUp()

        try:
            # try to find out whether youtube is happy with us this time
            # send a request and skip the test if there is an error
            ydl_opts = Youtube.get_ydl_opts()
            ydl_opts["logger"] = YoutubeDLLogger(self)
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                self.info_dict = ydl.download(
                    ["https://www.youtube.com/watch?v=wobbf3lb2nk"]
                )
        except (youtube_dl.utils.ExtractorError, youtube_dl.utils.DownloadError) as e:
            self.skipTest(f"Error when interacting with youtube, skipping test: {e}")

        # reduce the number for youtube playlists
        storage.set("max_playlist_items", "3")

        # if we want to make sure that the songs can be downloaded,
        # we could delete all songs in the test_cache folder
        # if os.path.split(os.path.dirname(settings.SONGS_CACHE_DIR))[1] == "test_cache":
        #    for member in os.listdir(settings.SONGS_CACHE_DIR):
        #        member_path = os.path.join(settings.SONGS_CACHE_DIR, member)
        #        if os.path.isfile(member_path):
        #            os.remove(member_path)

    def _poll_musiq_state(self, break_condition, timeout=1):
        """ Wrap the poll method of the super class to skip tests if Youtube doesn't play along."""
        try:
            return super()._poll_musiq_state(break_condition, timeout=timeout)
        except AssertionError:
            with open(os.path.join(settings.BASE_DIR, "logs/info.log")) as log:
                for line in log:
                    pass
                last_line = line
                if (
                    "ERROR: No video formats found" in last_line
                    or "ERROR: Unable to download webpage" in last_line
                ):
                    self.skipTest("Youtube provided no video formats")
            raise

    def _post_request(self, url, query=None, playlist=False):
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

    def test_query(self):
        self._post_request("request-music", "Eskimo Callboy MC Thunder Official Video")
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["externalUrl"], "https://www.youtube.com/watch?v=wobbf3lb2nk"
        )
        self.assertIn("MC Thunder", current_song["title"])
        self.assertAlmostEqual(current_song["duration"], 267, delta=1)

    def test_url(self):
        self._post_request(
            "request-music", "https://www.youtube.com/watch?v=wobbf3lb2nk"
        )
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["externalUrl"], "https://www.youtube.com/watch?v=wobbf3lb2nk"
        )
        self.assertIn("MC Thunder", current_song["title"])
        self.assertAlmostEqual(current_song["duration"], 267, delta=1)

    def test_playlist_url(self):
        self._post_request(
            "request-music",
            "https://www.youtube.com/playlist?list=PLvYcr2tNZuRquz0NQmBFF6ZhqFHSeOrbk",
            playlist=True,
        )
        state = self._poll_musiq_state(
            lambda state: state["musiq"]["currentSong"]
            and len(state["musiq"]["songQueue"]) == 2
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=60,
        )
        expected_playlist = [
            "https://www.youtube.com/watch?v=d0KWiDGi_ek",
            "https://www.youtube.com/watch?v=jcfcZfgyzm8",
            "https://www.youtube.com/watch?v=47P6CI7V8gM",
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

    def test_playlist_query(self):
        self._post_request(
            "request-music", "Muse Resistance Full Album HD", playlist=True
        )
        state = self._poll_musiq_state(
            lambda state: state["musiq"]["currentSong"]
            and len(state["musiq"]["songQueue"]) == 2
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=60,
        )
        expected_playlist = [
            "https://www.youtube.com/watch?v=d0KWiDGi_ek",
            "https://www.youtube.com/watch?v=jcfcZfgyzm8",
            "https://www.youtube.com/watch?v=47P6CI7V8gM",
        ]
        self.assertIn(state["musiq"]["currentSong"]["externalUrl"], expected_playlist)
        expected_playlist.remove(state["musiq"]["currentSong"]["externalUrl"])
        actual_playlist = [
            state["musiq"]["songQueue"][0]["externalUrl"],
            state["musiq"]["songQueue"][1]["externalUrl"],
        ]
        self.assertEqual(actual_playlist, expected_playlist)

    def test_autoplay(self):
        self._post_request(
            "request-music", "https://www.youtube.com/watch?v=wobbf3lb2nk"
        )
        self._poll_current_song()
        self.client.post(reverse("set-autoplay"), {"value": "true"})
        # make sure a song was downloaded into the queue
        state = self._poll_musiq_state(
            lambda state: len(state["musiq"]["songQueue"]) == 1
            and state["musiq"]["songQueue"][0]["internalUrl"],
            timeout=15,
        )
        old_id = state["musiq"]["songQueue"][0]["id"]

        self.client.post(reverse("skip"))
        # make sure another song is enqueued
        self._poll_musiq_state(
            lambda state: len(state["musiq"]["songQueue"]) == 1
            and state["musiq"]["songQueue"][0]["internalUrl"]
            and state["musiq"]["songQueue"][0]["id"] != old_id,
            timeout=15,
        )

    def test_radio(self):
        self._post_request(
            "request-music", "https://www.youtube.com/watch?v=w8KQmps-Sog"
        )
        self._poll_current_song()
        self._post_request("request-radio")
        # ensure that enough songs are enqueued
        self._poll_musiq_state(
            lambda state: len(state["musiq"]["songQueue"]) == 3
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=60,
        )
