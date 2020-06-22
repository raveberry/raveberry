import json
import time

from django.test import Client, TransactionTestCase
from django.urls import reverse

from tests import util


class RaveberryTest(TransactionTestCase):
    def setUp(self):
        from core.urls import BASE

        # store the base object from the server to allow mocking and direct method access
        self.base = BASE
        self.client = Client()
        util.admin_login(self.client)

        self.base.musiq.playback.start_loop()

    def tearDown(self):
        util.admin_login(self.client)

        self.base.musiq.playback.stop_loop()

    def _poll_state(self, state_url, break_condition, timeout=1):
        timeout *= 10
        counter = 0
        while counter < timeout:
            state = json.loads(self.client.get(reverse(state_url)).content)
            if break_condition(state):
                break
            time.sleep(0.1)
            counter += 1
        else:
            self.fail(f"enqueue timeout. state: {state}")
        return state

    def _poll_musiq_state(self, break_condition, timeout=1):
        return self._poll_state("musiq_state", break_condition, timeout=timeout)

    def _poll_lights_state(self, break_condition, timeout=1):
        return self._poll_state("lights_state", break_condition, timeout=timeout)
