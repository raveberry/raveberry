import json

from django.urls import reverse

from tests.music_test import MusicTest


class QueueTests(MusicTest):
    def setUp(self):
        super().setUp()
        self._setup_test_library()
        self._add_local_playlist()

    def test_add(self):
        suggestion = json.loads(
            self.client.get(reverse("random_suggestion"), {"playlist": "false"}).content
        )
        self.client.post(
            reverse("request_music"),
            {
                "key": suggestion["key"],
                "query": "",
                "playlist": "false",
                "platform": "local",
            },
        )
        self._poll_musiq_state(lambda state: len(state["song_queue"]) == 4)
        self.client.post(
            reverse("request_music"),
            {
                "key": suggestion["key"],
                "query": "",
                "playlist": "false",
                "platform": "local",
            },
        )
        self._poll_musiq_state(lambda state: len(state["song_queue"]) == 5)

    def test_remove(self):
        state = json.loads(self.client.get(reverse("musiq_state")).content)
        key = state["song_queue"][1]["id"]

        # removing a song shortens the queue by one
        self.client.post(reverse("remove_song"), {"key": str(key)})
        self._poll_musiq_state(lambda state: len(state["song_queue"]) == 2)

        # removing the same key another time should not change the queue length
        self.client.post(reverse("remove_song"), {"key": str(key)})
        self._poll_musiq_state(lambda state: len(state["song_queue"]) == 2)

        # choosing a new one should
        key = state["song_queue"][0]["id"]
        self.client.post(reverse("remove_song"), {"key": str(key)})
        self._poll_musiq_state(lambda state: len(state["song_queue"]) == 1)

    def test_prioritize(self):
        state = json.loads(self.client.get(reverse("musiq_state")).content)
        key = state["song_queue"][1]["id"]

        # the chosen key should now be at the first spot
        self.client.post(reverse("prioritize_song"), {"key": str(key)})
        self._poll_musiq_state(lambda state: state["song_queue"][0]["id"] == key)

        # another prioritize will not change this
        self.client.post(reverse("prioritize_song"), {"key": str(key)})
        self._poll_musiq_state(lambda state: state["song_queue"][0]["id"] == key)

        # another key will
        key = state["song_queue"][2]["id"]
        self.client.post(reverse("prioritize_song"), {"key": str(key)})
        self._poll_musiq_state(lambda state: state["song_queue"][0]["id"] == key)

    def test_reorder(self):
        state = json.loads(self.client.get(reverse("musiq_state")).content)
        # key1 -> key2 -> key3
        key1 = state["song_queue"][0]["id"]
        key2 = state["song_queue"][1]["id"]
        key3 = state["song_queue"][2]["id"]

        # key2 -> key1 -> key3
        # both keys are given
        self.client.post(
            reverse("reorder_song"),
            {"prev": str(key2), "element": str(key1), "next": str(key3)},
        )
        self._poll_musiq_state(
            lambda state: [song["id"] for song in state["song_queue"]]
            == [key2, key1, key3]
        )

        # key3 -> key2 -> key1
        # only the next key is given (=prioritize)
        self.client.post(
            reverse("reorder_song"),
            {"prev": "", "element": str(key3), "next": str(key2)},
        )
        self._poll_musiq_state(
            lambda state: [song["id"] for song in state["song_queue"]]
            == [key3, key2, key1]
        )

        # key2 -> key1 -> key3
        # only the prev key is given (=deprioritize)
        self.client.post(
            reverse("reorder_song"),
            {"prev": str(key1), "element": str(key3), "next": ""},
        )
        self._poll_musiq_state(
            lambda state: [song["id"] for song in state["song_queue"]]
            == [key2, key1, key3]
        )

    def test_remove_all(self):
        self.client.post(reverse("remove_all"))
        self._poll_musiq_state(lambda state: len(state["song_queue"]) == 0)


class QueueVotingTests(MusicTest):
    def setUp(self):
        super().setUp()
        self._setup_test_library()
        self._add_local_playlist()

        self.client.post(reverse("set_voting_system"), {"value": "true"})
        self._poll_state("settings_state", lambda state: state["voting_system"] == True)
        self.client.logout()

    def test_votes(self):
        state = json.loads(self.client.get(reverse("musiq_state")).content)
        # key1 -> key2 -> key3
        key1 = state["song_queue"][0]["id"]
        key2 = state["song_queue"][1]["id"]
        key3 = state["song_queue"][2]["id"]

        self.client.post(reverse("vote_up_song"), {"key": str(key2)})
        self.client.post(reverse("vote_up_song"), {"key": str(key3)})
        self._poll_musiq_state(
            lambda state: [song["id"] for song in state["song_queue"]]
            == [key2, key3, key1]
        )

        self.client.post(reverse("vote_up_song"), {"key": str(key1)})
        self._poll_musiq_state(
            lambda state: [song["id"] for song in state["song_queue"]]
            == [key1, key2, key3]
        )

        self.client.post(reverse("vote_down_song"), {"key": str(key2)})
        self.client.post(reverse("vote_down_song"), {"key": str(key2)})
        self.client.post(reverse("vote_down_song"), {"key": str(key1)})
        self._poll_musiq_state(
            lambda state: [song["id"] for song in state["song_queue"]]
            == [key3, key1, key2]
        )

    def test_vote_remove(self):
        state = json.loads(self.client.get(reverse("musiq_state")).content)
        # key1 -> key2 -> key3
        key1 = state["song_queue"][0]["id"]
        key2 = state["song_queue"][1]["id"]
        key3 = state["song_queue"][2]["id"]

        for _ in range(3):
            self.client.post(reverse("vote_down_song"), {"key": str(key2)})
        self._poll_musiq_state(
            lambda state: [song["id"] for song in state["song_queue"]] == [key1, key3]
        )

    def test_vote_skip(self):
        state = json.loads(self.client.get(reverse("musiq_state")).content)
        # key1 -> key2 -> key3
        key = state["current_song"]["queue_key"]

        for _ in range(3):
            self.client.post(reverse("vote_down_song"), {"key": str(key)})
        self._poll_musiq_state(lambda state: len(state["song_queue"]) == 2)
