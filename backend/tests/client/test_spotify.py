import os

from django.urls import reverse

from core.models import Setting
from tests.music_test import MusicTest


class SpotifyTests(MusicTest):
    def setUp(self) -> None:
        try:
            username = os.environ["SPOTIFY_USERNAME"]
            password = os.environ["SPOTIFY_PASSWORD"]
            client_id = os.environ["SPOTIFY_CLIENT_ID"]
            client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
        except KeyError:
            self.skipTest("No spotify credentials provided.")

        super().setUp()

        Setting.objects.update_or_create(
            key="spotify_username", defaults={"value": username}
        )
        Setting.objects.update_or_create(
            key="spotify_password", defaults={"value": password}
        )
        Setting.objects.update_or_create(
            key="spotify_client_id", defaults={"value": client_id}
        )
        Setting.objects.update_or_create(
            key="spotify_client_secret", defaults={"value": client_secret}
        )

        self.client.post(reverse("set-spotify-enabled"), {"value": "true"})

    def test_query(self) -> None:
        self.client.post(
            reverse("request-music"),
            {
                "query": "Eskimo Callboy MC Thunder",
                "playlist": "false",
                "platform": "spotify",
            },
        )
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["externalUrl"],
            "https://open.spotify.com/track/7synI8hwKZiEsf11m1tqto",
        )
        self.assertEqual(current_song["artist"], "Eskimo Callboy")
        self.assertEqual(current_song["title"], "MC Thunder")
        self.assertAlmostEqual(current_song["duration"], 230, delta=1)

    def test_url(self) -> None:
        self.client.post(
            reverse("request-music"),
            {
                "query": "https://open.spotify.com/track/4EyPadLFhtWojU7mkT5hqT",
                "playlist": "false",
                "platform": "spotify",
            },
        )
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["externalUrl"],
            "https://open.spotify.com/track/4EyPadLFhtWojU7mkT5hqT",
        )
        self.assertEqual(current_song["artist"], "Bring Me The Horizon")
        self.assertEqual(current_song["title"], "Avalanche")
        self.assertAlmostEqual(current_song["duration"], 262, delta=1)

    def test_playlist_url(self) -> None:
        self.client.post(
            reverse("request-music"),
            {
                "query": "https://open.spotify.com/playlist/2Ja8Y9o9awbq6F9Sl1AcwI",
                "playlist": "true",
                "platform": "spotify",
            },
        )
        state = self._poll_musiq_state(
            lambda state: state["musiq"]["currentSong"]
            and len(state["musiq"]["songQueue"]) == 4
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=10,
        )
        self.assertEqual(
            state["musiq"]["currentSong"]["externalUrl"],
            "https://open.spotify.com/track/5wq8wceQvaFlOZovDtfr0j",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][0]["externalUrl"],
            "https://open.spotify.com/track/5rupf5kRDLhhFPxH15ZmBF",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][1]["externalUrl"],
            "https://open.spotify.com/track/3IwAWUa9JeTbwumBPvnOj9",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][2]["externalUrl"],
            "https://open.spotify.com/track/3vMrcGW4o35zY6vXjWb1p7",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][3]["externalUrl"],
            "https://open.spotify.com/track/6Jf7Sx68vsWFKeWjOxcLhQ",
        )

    def test_playlist_query(self):
        self.client.post(
            reverse("request-music"),
            {
                "query": "Muse Resistance Album",
                "playlist": "true",
                "platform": "spotify",
            },
        )
        state = self._poll_musiq_state(
            lambda state: state["musiq"]["currentSong"]
            and len(state["musiq"]["songQueue"]) == 4
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=10,
        )
        self.assertEqual(
            state["musiq"]["currentSong"]["externalUrl"],
            "https://open.spotify.com/track/5wq8wceQvaFlOZovDtfr0j",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][0]["externalUrl"],
            "https://open.spotify.com/track/5rupf5kRDLhhFPxH15ZmBF",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][1]["externalUrl"],
            "https://open.spotify.com/track/3IwAWUa9JeTbwumBPvnOj9",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][2]["externalUrl"],
            "https://open.spotify.com/track/3vMrcGW4o35zY6vXjWb1p7",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][3]["externalUrl"],
            "https://open.spotify.com/track/6Jf7Sx68vsWFKeWjOxcLhQ",
        )

    def test_autoplay(self):
        self.client.post(
            reverse("request-music"),
            {
                "query": "https://open.spotify.com/track/4VqPOruhp5EdPBeR92t6lQ",
                "playlist": "false",
                "platform": "spotify",
            },
        )
        self._poll_current_song()
        self.client.post(reverse("set-autoplay"), {"value": "true"})
        # make sure a song was downloaded into the queue
        state = self._poll_musiq_state(
            lambda state: len(state["musiq"]["songQueue"]) == 1
            and state["musiq"]["songQueue"][0]["internalUrl"],
            timeout=10,
        )
        old_id = state["musiq"]["songQueue"][0]["id"]

        self.client.post(reverse("skip"))
        self._wait_for_new_song(old_id)

    def test_radio(self):
        self.client.post(
            reverse("request-music"),
            {
                "query": "https://open.spotify.com/track/4VqPOruhp5EdPBeR92t6lQ",
                "playlist": "false",
                "platform": "spotify",
            },
        )
        self._poll_current_song()
        self.client.post(reverse("request-radio"))
        # ensure that 5 songs are enqueued
        self._poll_musiq_state(
            lambda state: len(state["musiq"]["songQueue"]) == 5
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=10,
        )
