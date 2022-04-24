import json

from django.urls import reverse

from tests.music_test import MusicTest


class LocaldriveTests(MusicTest):
    def setUp(self) -> None:
        super().setUp()
        self._setup_test_library()

    def test_suggested_song(self) -> None:
        suggestion = json.loads(
            self.client.get(
                reverse("offline-suggestions"),
                {"term": "backbeat", "playlist": "false"},
            ).content
        )[-1]
        self._request_suggestion(suggestion["key"])
        state = self._poll_musiq_state(lambda state: state["musiq"]["currentSong"])
        current_song = state["musiq"]["currentSong"]
        self.assertEqual(
            current_song["externalUrl"], "local_library/other/Backbeat.mp3"
        )
        self.assertAlmostEqual(current_song["duration"], 46, delta=1)
        self.assertEqual(current_song["artist"], "Kevin MacLeod")
        self.assertEqual(current_song["title"], "Backbeat")

    def test_suggested_playlist(self) -> None:
        state = self._add_local_playlist()
        self.assertEqual(
            state["musiq"]["currentSong"]["externalUrl"],
            "local_library/other/Backbeat.mp3",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][0]["externalUrl"],
            "local_library/other/Forest Frolic Loop.mp3",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][1]["externalUrl"],
            "local_library/other/Village Tarantella.mp3",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][2]["externalUrl"],
            "local_library/heroes/Gothamlicious.mp3",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][3]["externalUrl"],
            "local_library/heroes/New Hero in Town.mp3",
        )

    def test_autoplay(self) -> None:
        suggestion = json.loads(
            self.client.get(
                reverse("offline-suggestions"),
                {"term": "backbeat", "playlist": "false"},
            ).content
        )[-1]
        self.client.post(
            reverse("request-music"),
            {
                "key": suggestion["key"],
                "query": "",
                "playlist": "false",
                "platform": "local",
            },
        )
        self._poll_current_song()
        self.client.post(reverse("set-autoplay"), {"value": "true"})
        # make sure a song was downloaded into the queue
        state = self._poll_musiq_state(
            lambda state: len(state["musiq"]["songQueue"]) == 1
            and state["musiq"]["songQueue"][0]["internalUrl"]
        )
        old_id = state["musiq"]["songQueue"][0]["id"]

        self.client.post(reverse("skip"))
        self._wait_for_new_song(old_id)

    def test_radio(self) -> None:
        suggestion = json.loads(
            self.client.get(
                reverse("offline-suggestions"),
                {"term": "backbeat", "playlist": "false"},
            ).content
        )[-1]
        self._request_suggestion(suggestion["key"])
        self._poll_current_song()
        self.client.post(reverse("request-radio"))
        # ensure that at least 2 songs are enqueued (the ogg folder only has two files)
        self._poll_musiq_state(
            lambda state: len(state["musiq"]["songQueue"]) >= 1
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=3,
        )
