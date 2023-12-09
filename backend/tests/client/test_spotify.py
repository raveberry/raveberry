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
            key="spotify_mopidy_client_id", defaults={"value": client_id}
        )
        Setting.objects.update_or_create(
            key="spotify_mopidy_client_secret", defaults={"value": client_secret}
        )

        self.client.post(reverse("set-spotify-enabled"), {"value": "true"})

    def test_query(self) -> None:
        self.client.post(
            reverse("request-music"),
            {
                "query": "Myuu Collapse",
                "playlist": "false",
                "platform": "spotify",
            },
        )
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["externalUrl"],
            "https://open.spotify.com/track/0o261w05EPiGfxNtVlWn6m",
        )
        self.assertEqual(current_song["artist"], "Myuu")
        self.assertEqual(current_song["title"], "Collapse")
        self.assertAlmostEqual(current_song["duration"], 200, delta=1)

    def test_url(self) -> None:
        self.client.post(
            reverse("request-music"),
            {
                "query": "https://open.spotify.com/track/0o261w05EPiGfxNtVlWn6m",
                "playlist": "false",
                "platform": "spotify",
            },
        )
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["externalUrl"],
            "https://open.spotify.com/track/0o261w05EPiGfxNtVlWn6m",
        )
        self.assertEqual(current_song["artist"], "Myuu")
        self.assertEqual(current_song["title"], "Collapse")
        self.assertAlmostEqual(current_song["duration"], 200, delta=1)

    def test_playlist_url(self) -> None:
        self.client.post(
            reverse("request-music"),
            {
                "query": "https://open.spotify.com/album/1d3X0w0kdfqcvOVNfnthhP",
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
            "https://open.spotify.com/track/3uYgQ819EExqKhxr2ILFok",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][0]["externalUrl"],
            "https://open.spotify.com/track/43TuwMfK9h8b0rtbkdWCYJ",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][1]["externalUrl"],
            "https://open.spotify.com/track/7JsBddAbtHCjdEtMobVfyL",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][2]["externalUrl"],
            "https://open.spotify.com/track/01Rk5ZPcMeQLxBEAcxZMju",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][3]["externalUrl"],
            "https://open.spotify.com/track/7y6D7PitToNpVycQ2WuUPi",
        )

    def test_playlist_query(self):
        self.client.post(
            reverse("request-music"),
            {
                "query": "Myuu The Dark Piano, Vol. 3 Album",
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
            "https://open.spotify.com/track/4TCltHCj9FTS36rK7XZXMx",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][0]["externalUrl"],
            "https://open.spotify.com/track/1eo3KheI9C0uvp4PlmTdrc",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][1]["externalUrl"],
            "https://open.spotify.com/track/1UnNQ4xqCGFH279AQi68XE",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][2]["externalUrl"],
            "https://open.spotify.com/track/0161x17UsgPtluoi4OIVI8",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][3]["externalUrl"],
            "https://open.spotify.com/track/7yISlDyywvoXKgz6WxRKAI",
        )

    def test_autoplay(self):
        self.client.post(
            reverse("request-music"),
            {
                "query": "https://open.spotify.com/track/0o261w05EPiGfxNtVlWn6m",
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
                "query": "https://open.spotify.com/track/0o261w05EPiGfxNtVlWn6m",
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
