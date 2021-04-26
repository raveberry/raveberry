import json
import os
import time

from django.conf import settings
from django.urls import reverse
from mopidyapi import MopidyAPI

from tests import util
from tests.raveberry_test import RaveberryTest


class MusicTest(RaveberryTest):
    def setUp(self):
        super().setUp()

        # mute player for testing
        self.player = MopidyAPI(host=settings.MOPIDY_HOST)
        self.player.mixer.set_volume(0)
        # reduce number of downloaded songs for the test
        self.client.post(reverse("set-max-playlist-items"), {"value": "5"})

    def tearDown(self):
        util.admin_login(self.client)

        # restore player state
        self.client.post(reverse("set-autoplay"), {"value": "false"})
        self._poll_musiq_state(lambda state: not state["musiq"]["autoplay"])

        # ensure that the player is not waiting for a song to finish
        self.client.post(reverse("remove-all"))
        self._poll_musiq_state(lambda state: len(state["musiq"]["songQueue"]) == 0)
        self.client.post(reverse("skip"))
        self._poll_musiq_state(lambda state: not state["musiq"]["currentSong"])

        super().tearDown()

    def _setup_test_library(self):
        if not util.download_test_library():
            self.skipTest("could not download test library")

        test_library = os.path.join(settings.TEST_CACHE_DIR, "test_library")
        self.client.post(reverse("scan-library"), {"library_path": test_library})
        # need to split the scan_progress as it contains no-break spaces
        self._poll_state(
            "settings-state",
            lambda state: " ".join(
                state["settings"]["scanProgress"].split()
            ).startswith("6 / 6 / "),
        )
        self.client.post(reverse("create-playlists"))
        self._poll_state(
            "settings-state",
            lambda state: " ".join(
                state["settings"]["scanProgress"].split()
            ).startswith("6 / 6 / "),
        )

    def _poll_current_song(self):
        state = self._poll_musiq_state(
            lambda state: state["musiq"]["currentSong"], timeout=10
        )
        current_song = state["musiq"]["currentSong"]
        return current_song

    def _add_local_playlist(self):
        suggestion = json.loads(
            self.client.get(
                reverse("get-suggestions"), {"term": "hard rock", "playlist": "true"}
            ).content
        )[-1]
        self.client.post(
            reverse("request-music"),
            {
                "key": suggestion["key"],
                "query": "",
                "playlist": "true",
                "platform": "local",
            },
        )
        state = self._poll_musiq_state(
            lambda state: state["musiq"]["currentSong"]
            and len(state["musiq"]["songQueue"]) == 3
            and all(song["internalUrl"] for song in state["musiq"]["songQueue"]),
            timeout=3,
        )
        return state
