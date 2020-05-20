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
                reverse("suggestions"), {"term": "sk8board", "playlist": "false"}
            ).content
        )[-1]
        self.client.post(
            reverse("request_music"),
            {
                "key": suggestion["key"],
                "query": "",
                "playlist": "false",
                "platform": "local",
            },
        )
        state = self._poll_musiq_state(lambda state: state["current_song"])
        current_song = state["current_song"]
        self.assertEqual(
            current_song["external_url"], "local_library/Techno/Sk8board.mp3"
        )
        self.assertEqual(current_song["artist"], "AUDIONAUTIX.COM")
        self.assertEqual(current_song["title"], "SK8BOARD")
        self.assertEqual(current_song["duration"], 126)

    def test_suggested_playlist(self):
        state = self._add_local_playlist()
        self.assertEqual(
            state["current_song"]["external_url"],
            "local_library/Hard Rock/ChecksForFree.mp3",
        )
        self.assertEqual(
            state["song_queue"][0]["external_url"],
            "local_library/Hard Rock/HeavyAction.mp3",
        )
        self.assertEqual(
            state["song_queue"][1]["external_url"],
            "local_library/Hard Rock/HiFiBrutality.mp3",
        )
        self.assertEqual(
            state["song_queue"][2]["external_url"],
            "local_library/Hard Rock/LongLiveDeath.mp3",
        )

    def test_autoplay(self):
        suggestion = json.loads(
            self.client.get(
                reverse("suggestions"), {"term": "checks", "playlist": "false"}
            ).content
        )[-1]
        self.client.post(
            reverse("request_music"),
            {
                "key": suggestion["key"],
                "query": "",
                "playlist": "false",
                "platform": "local",
            },
        )
        self._poll_current_song()
        self.client.post(reverse("set_autoplay"), {"value": "true"})
        # make sure a song was downloaded into the queue
        state = self._poll_musiq_state(
            lambda state: len(state["song_queue"]) == 1
            and state["song_queue"][0]["internal_url"]
        )
        old_id = state["song_queue"][0]["id"]

        self.client.post(reverse("skip_song"))
        # make sure another song is enqueued
        self._poll_musiq_state(
            lambda state: len(state["song_queue"]) == 1
            and state["song_queue"][0]["internal_url"]
            and state["song_queue"][0]["id"] != old_id
        )

    def test_radio(self):
        suggestion = json.loads(
            self.client.get(
                reverse("suggestions"), {"term": "checks", "playlist": "false"}
            ).content
        )[-1]
        self.client.post(
            reverse("request_music"),
            {
                "key": suggestion["key"],
                "query": "",
                "playlist": "false",
                "platform": "local",
            },
        )
        self._poll_current_song()
        self.client.post(reverse("request_radio"))
        # ensure that the 4 songs of the album are enqueued
        self._poll_musiq_state(
            lambda state: len(state["song_queue"]) == 4
            and all(song["internal_url"] for song in state["song_queue"]),
            timeout=3,
        )
