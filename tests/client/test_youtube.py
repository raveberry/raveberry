import os

from django.conf import settings
from django.urls import reverse

from tests.music_test import MusicTest


class YoutubeTests(MusicTest):
    def setUp(self):
        super().setUp()

        # clear test cache; ensure that it's the test directory
        if os.path.split(os.path.dirname(settings.SONGS_CACHE_DIR))[1] == "test_cache":
            for member in os.listdir(settings.SONGS_CACHE_DIR):
                member_path = os.path.join(settings.SONGS_CACHE_DIR, member)
                if os.path.isfile(member_path):
                    os.remove(member_path)

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
            self.skipTest("This IP sent too many requests to Youtube does not like it.")

    def test_query(self):
        self._post_request("request_music", "Eskimo Callboy MC Thunder")
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["external_url"], "https://www.youtube.com/watch?v=wobbf3lb2nk"
        )
        self.assertEqual(current_song["artist"], "Eskimo Callboy")
        self.assertEqual(current_song["title"], "MC Thunder")
        self.assertEqual(current_song["duration"], 267)

    def test_url(self):
        self._post_request(
            "request_music", "https://www.youtube.com/watch?v=UNaYpBpRJOY"
        )
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["external_url"], "https://www.youtube.com/watch?v=UNaYpBpRJOY"
        )
        self.assertEqual(current_song["artist"], "Bring Me the Horizon")
        self.assertEqual(current_song["title"], "Avalanche")
        self.assertEqual(current_song["duration"], 275)

    def test_playlist_url(self):
        self._post_request(
            "request_music",
            "https://www.youtube.com/playlist?list=PLiS9Gj9LFFFxFrsk9vKmMWAd4TCrOgYd3",
            playlist=True,
        )
        state = self._poll_musiq_state(
            lambda state: len(state["song_queue"]) == 2
            and all(song["confirmed"] for song in state["song_queue"]),
            timeout=60,
        )
        self.assertEqual(
            state["current_song"]["external_url"],
            "https://www.youtube.com/watch?v=LGamaKv0zNg",
        )
        self.assertEqual(
            state["song_queue"][0]["external_url"],
            "https://www.youtube.com/watch?v=eiCimeZi3-g",
        )
        self.assertEqual(
            state["song_queue"][1]["external_url"],
            "https://www.youtube.com/watch?v=CaY36kVk-cU",
        )

    def test_playlist_query(self):
        self._post_request("request_music", "Muse Resistance Album", playlist=True)
        state = self._poll_musiq_state(
            lambda state: len(state["song_queue"]) == 4
            and all(song["confirmed"] for song in state["song_queue"]),
            timeout=60,
        )
        self.assertEqual(
            state["current_song"]["external_url"],
            "https://www.youtube.com/watch?v=d0KWiDGi_ek",
        )
        self.assertEqual(
            state["song_queue"][0]["external_url"],
            "https://www.youtube.com/watch?v=jcfcZfgyzm8",
        )
        self.assertEqual(
            state["song_queue"][1]["external_url"],
            "https://www.youtube.com/watch?v=47P6CI7V8gM",
        )
        self.assertEqual(
            state["song_queue"][2]["external_url"],
            "https://www.youtube.com/watch?v=-5-K51jHQ6k",
        )
        self.assertEqual(
            state["song_queue"][3]["external_url"],
            "https://www.youtube.com/watch?v=ZsbwAGZHybA",
        )

    def test_autoplay(self):
        self._post_request(
            "request_music", "https://www.youtube.com/watch?v=w8KQmps-Sog"
        )
        self._poll_current_song()
        self.client.post(reverse("set_autoplay"), {"value": "true"})
        # make sure a song was downloaded into the queue
        state = self._poll_musiq_state(
            lambda state: len(state["song_queue"]) == 1
            and state["song_queue"][0]["confirmed"],
            timeout=10,
        )
        old_id = state["song_queue"][0]["id"]

        self.client.post(reverse("skip_song"))
        # make sure another song is enqueued
        self._poll_musiq_state(
            lambda state: len(state["song_queue"]) == 1
            and state["song_queue"][0]["confirmed"]
            and state["song_queue"][0]["id"] != old_id,
            timeout=10,
        )

    def test_radio(self):
        self._post_request(
            "request_music", "https://www.youtube.com/watch?v=w8KQmps-Sog"
        )
        self._poll_current_song()
        self._post_request("request_radio")
        # ensure that 5 songs are enqueued
        self._poll_musiq_state(
            lambda state: len(state["song_queue"]) == 5
            and all(song["confirmed"] for song in state["song_queue"]),
            timeout=60,
        )
