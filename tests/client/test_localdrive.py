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
                reverse("get-suggestions"), {"term": "impact", "playlist": "false"}
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
        # which song is enqueued is not deterministic, as they all are named identically…
        # self.assertEqual(
        #    current_song["externalUrl"], "local_library/ogg/file_example_OOG_1MG.ogg"
        # )
        # self.assertEqual(current_song["duration"], 27)
        self.assertEqual(current_song["artist"], "Kevin MacLeod")
        self.assertEqual(current_song["title"], "Impact Moderato")

    def test_suggested_playlist(self):
        state = self._add_local_playlist()
        self.assertEqual(
            state["musiq"]["currentSong"]["externalUrl"],
            "local_library/ogg/file_example_OOG_1MG.ogg",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][0]["externalUrl"],
            "local_library/ogg/file_example_OOG_2MG.ogg",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][1]["externalUrl"],
            "local_library/ogg/file_example_OOG_1MG.ogg",
        )
        self.assertEqual(
            state["musiq"]["songQueue"][2]["externalUrl"],
            "local_library/ogg/file_example_OOG_2MG.ogg",
        )

    def test_autoplay(self):
        suggestion = json.loads(
            self.client.get(
                reverse("get-suggestions"), {"term": "impact", "playlist": "false"}
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
                reverse("get-suggestions"), {"term": "impact", "playlist": "false"}
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
        # ensure that at least 2 songs are enqueued (the ogg folder only has two files)
        self._poll_musiq_state(
            lambda state: len(state["musiq"]["songQueue"]) >= 1
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=3,
        )
