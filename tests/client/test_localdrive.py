import json

from django.urls import reverse

from tests.music_test import MusicTest


class LocaldriveTests(MusicTest):
    def setUp(self):
        super().setUp()
        self._setup_test_library()

    def test_suggested_song(self):
        suggestion = json.loads(
            self.client.get(
                reverse("get-suggestions"), {"term": "sk8board", "playlist": "false"}
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
        state = self._poll_musiq_state(lambda state: state["musiq"]["currentSong"])
        current_song = state["musiq"]["currentSong"]
        self.assertEqual(
            current_song["externalUrl"], "local_library/Techno/Sk8board.mp3"
        )
        self.assertEqual(current_song["artist"], "AUDIONAUTIX.COM")
        self.assertEqual(current_song["title"], "SK8BOARD")
        self.assertEqual(current_song["duration"], 126)

    def test_suggested_playlist(self):
        state = self._add_local_playlist()
        self.assertEqual(
            state["musiq"]["currentSong"]["externalUrl"],
            "local_library/Hard Rock/ChecksForFree.mp3",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][0]["externalUrl"],
            "local_library/Hard Rock/HeavyAction.mp3",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][1]["externalUrl"],
            "local_library/Hard Rock/HiFiBrutality.mp3",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][2]["externalUrl"],
            "local_library/Hard Rock/LongLiveDeath.mp3",
        )

    def test_autoplay(self):
        suggestion = json.loads(
            self.client.get(
                reverse("get-suggestions"), {"term": "checks", "playlist": "false"}
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
        # make sure another song is enqueued
        self._poll_musiq_state(
            lambda state: len(state["musiq"]["songQueue"]) == 1
            and state["musiq"]["songQueue"][0]["internalUrl"]
            and state["musiq"]["songQueue"][0]["id"] != old_id
        )

    def test_radio(self):
        suggestion = json.loads(
            self.client.get(
                reverse("get-suggestions"), {"term": "checks", "playlist": "false"}
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
        self.client.post(reverse("request-radio"))
        # ensure that the 4 songs of the album are enqueued
        self._poll_musiq_state(
            lambda state: len(state["musiq"]["songQueue"]) == 4
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=3,
        )
