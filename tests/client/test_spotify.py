import os

from django.urls import reverse

from core.models import Setting
from tests.music_test import MusicTest


class SpotifyTests(MusicTest):
    def setUp(self):
        super().setUp()

        try:
            client_id = os.environ["SPOTIFY_CLIENT_ID"]
            client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
        except KeyError:
            self.skipTest("No spotify credentials provided.")

        Setting.objects.update_or_create(
            key="spotify_client_id", defaults={"value": client_id}
        )
        Setting.objects.update_or_create(
            key="spotify_client_secret", defaults={"value": client_secret}
        )

        self.client.post(reverse("set_spotify_enabled"), {"value": "true"})

    def test_query(self):
        self.client.post(
            reverse("request_music"),
            {
                "query": "Eskimo Callboy MC Thunder",
                "playlist": "false",
                "platform": "spotify",
            },
        )
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["external_url"],
            "https://open.spotify.com/track/7synI8hwKZiEsf11m1tqto",
        )
        self.assertEqual(current_song["artist"], "Eskimo Callboy")
        self.assertEqual(current_song["title"], "MC Thunder")
        self.assertEqual(current_song["duration"], 230)

    def test_url(self):
        self.client.post(
            reverse("request_music"),
            {
                "query": "https://open.spotify.com/track/4EyPadLFhtWojU7mkT5hqT",
                "playlist": "false",
                "platform": "spotify",
            },
        )
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["external_url"],
            "https://open.spotify.com/track/4EyPadLFhtWojU7mkT5hqT",
        )
        self.assertEqual(current_song["artist"], "Bring Me The Horizon")
        self.assertEqual(current_song["title"], "Avalanche")
        self.assertEqual(current_song["duration"], 262)

    def test_playlist_url(self):
        self.client.post(
            reverse("request_music"),
            {
                "query": "https://open.spotify.com/playlist/2Ja8Y9o9awbq6F9Sl1AcwI",
                "playlist": "true",
                "platform": "spotify",
            },
        )
        state = self._poll_musiq_state(
            lambda state: state["current_song"]
            and len(state["song_queue"]) == 4
            and all(song["internal_url"] for song in state["song_queue"]),
            timeout=60,
        )
        self.assertEqual(
            state["current_song"]["external_url"],
            "https://open.spotify.com/track/5wq8wceQvaFlOZovDtfr0j",
        )
        self.assertEqual(
            state["song_queue"][0]["external_url"],
            "https://open.spotify.com/track/5rupf5kRDLhhFPxH15ZmBF",
        )
        self.assertEqual(
            state["song_queue"][1]["external_url"],
            "https://open.spotify.com/track/3IwAWUa9JeTbwumBPvnOj9",
        )
        self.assertEqual(
            state["song_queue"][2]["external_url"],
            "https://open.spotify.com/track/3vMrcGW4o35zY6vXjWb1p7",
        )
        self.assertEqual(
            state["song_queue"][3]["external_url"],
            "https://open.spotify.com/track/6Jf7Sx68vsWFKeWjOxcLhQ",
        )

    def test_playlist_query(self):
        self.client.post(
            reverse("request_music"),
            {
                "query": "Muse Resistance Album",
                "playlist": "true",
                "platform": "spotify",
            },
        )
        state = self._poll_musiq_state(
            lambda state: state["current_song"]
            and len(state["song_queue"]) == 4
            and all(song["internal_url"] for song in state["song_queue"]),
            timeout=60,
        )
        self.assertEqual(
            state["current_song"]["external_url"],
            "https://open.spotify.com/track/5wq8wceQvaFlOZovDtfr0j",
        )
        self.assertEqual(
            state["song_queue"][0]["external_url"],
            "https://open.spotify.com/track/5rupf5kRDLhhFPxH15ZmBF",
        )
        self.assertEqual(
            state["song_queue"][1]["external_url"],
            "https://open.spotify.com/track/3IwAWUa9JeTbwumBPvnOj9",
        )
        self.assertEqual(
            state["song_queue"][2]["external_url"],
            "https://open.spotify.com/track/3vMrcGW4o35zY6vXjWb1p7",
        )
        self.assertEqual(
            state["song_queue"][3]["external_url"],
            "https://open.spotify.com/track/6Jf7Sx68vsWFKeWjOxcLhQ",
        )

    def test_autoplay(self):
        self.client.post(
            reverse("request_music"),
            {
                "query": "https://open.spotify.com/track/4VqPOruhp5EdPBeR92t6lQ",
                "playlist": "false",
                "platform": "spotify",
            },
        )
        self._poll_current_song()
        self.client.post(reverse("set_autoplay"), {"value": "true"})
        # make sure a song was downloaded into the queue
        state = self._poll_musiq_state(
            lambda state: len(state["song_queue"]) == 1
            and state["song_queue"][0]["internal_url"],
            timeout=10,
        )
        old_id = state["song_queue"][0]["id"]

        self.client.post(reverse("skip_song"))
        # make sure another song is enqueued
        self._poll_musiq_state(
            lambda state: len(state["song_queue"]) == 1
            and state["song_queue"][0]["internal_url"]
            and state["song_queue"][0]["id"] != old_id,
            timeout=10,
        )

    def test_radio(self):
        self.client.post(
            reverse("request_music"),
            {
                "query": "https://open.spotify.com/track/4VqPOruhp5EdPBeR92t6lQ",
                "playlist": "false",
                "platform": "spotify",
            },
        )
        self._poll_current_song()
        self.client.post(reverse("request_radio"))
        # ensure that 5 songs are enqueued
        self._poll_musiq_state(
            lambda state: len(state["song_queue"]) == 5
            and all(song["internal_url"] for song in state["song_queue"]),
            timeout=60,
        )
