import os

from django.urls import reverse

from core.models import Setting
from tests.music_test import MusicTest


class JamendoTests(MusicTest):
    def setUp(self):
        super().setUp()

        try:
            client_id = os.environ["JAMENDO_CLIENT_ID"]
        except KeyError:
            self.skipTest("No jamendo credentials provided.")

        Setting.objects.update_or_create(
            key="jamendo_client_id", defaults={"value": client_id}
        )

        self.client.post(reverse("set-max-playlist-items"), {"value": "4"})
        self.client.post(reverse("set-jamendo-enabled"), {"value": "true"})

    def test_query(self):
        self.client.post(
            reverse("request-music"),
            {
                "query": " Africa The Cradle of Life (Epic Version)",
                "playlist": "false",
                "platform": "jamendo",
            },
        )
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["externalUrl"], "https://www.jamendo.com/track/1646305"
        )
        self.assertEqual(current_song["artist"], "Grégoire Lourme")
        self.assertEqual(
            current_song["title"], "Africa The Cradle of Life (Epic Version)"
        )
        self.assertEqual(current_song["duration"], 294)

    def test_url(self):
        self.client.post(
            reverse("request-music"),
            {
                "query": "https://www.jamendo.com/track/1646305/africa-the-cradle-of-life-epic-version",
                "playlist": "false",
                "platform": "jamendo",
            },
        )
        current_song = self._poll_current_song()
        self.assertEqual(
            current_song["externalUrl"], "https://www.jamendo.com/track/1646305"
        )
        self.assertEqual(current_song["artist"], "Grégoire Lourme")
        self.assertEqual(
            current_song["title"], "Africa The Cradle of Life (Epic Version)"
        )
        self.assertEqual(current_song["duration"], 294)

    def test_playlist_url(self):
        self.client.post(
            reverse("request-music"),
            {
                "query": "https://www.jamendo.com/playlist/500510544/long-live-the-king",
                "playlist": "true",
                "platform": "jamendo",
            },
        )
        state = self._poll_musiq_state(
            lambda state: state["musiq"]["currentSong"]
            and len(state["musiq"]["songQueue"]) == 3
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=10,
        )
        expected_playlist = sorted(
            [
                "https://www.jamendo.com/track/1646305",
                "https://www.jamendo.com/track/1500596",
                "https://www.jamendo.com/track/1552710",
                "https://www.jamendo.com/track/1069870",
            ]
        )
        self.assertIn(state["musiq"]["currentSong"]["externalUrl"], expected_playlist)
        expected_playlist.remove(state["musiq"]["currentSong"]["externalUrl"])
        actual_playlist = sorted(
            [
                state["musiq"]["songQueue"][0]["externalUrl"],
                state["musiq"]["songQueue"][1]["externalUrl"],
                state["musiq"]["songQueue"][2]["externalUrl"],
            ]
        )
        self.assertEqual(actual_playlist, expected_playlist)

    def test_playlist_query(self):
        # https://www.jamendo.com/playlist/500502579/long-live-the-king
        self.client.post(
            reverse("request-music"),
            {"query": "long live the king", "playlist": "true", "platform": "jamendo"},
        )
        state = self._poll_musiq_state(
            lambda state: state["musiq"]["currentSong"]
            and len(state["musiq"]["songQueue"]) == 3
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=10,
        )
        expected_playlist = sorted(
            [
                "https://www.jamendo.com/track/1646305",
                "https://www.jamendo.com/track/1552710",
                "https://www.jamendo.com/track/939496",
                "https://www.jamendo.com/track/1143802",
            ]
        )
        self.assertIn(state["musiq"]["currentSong"]["externalUrl"], expected_playlist)
        expected_playlist.remove(state["musiq"]["currentSong"]["externalUrl"])
        actual_playlist = sorted(
            [
                state["musiq"]["songQueue"][0]["externalUrl"],
                state["musiq"]["songQueue"][1]["externalUrl"],
                state["musiq"]["songQueue"][2]["externalUrl"],
            ]
        )
        self.assertEqual(actual_playlist, expected_playlist)
