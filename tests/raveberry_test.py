import json
import time
from threading import Thread

from celery.contrib.testing.worker import start_worker
from django.test import Client, TransactionTestCase, SimpleTestCase
from django.urls import reverse

from core import redis, models
from core.celery import app
from core.musiq import playback
from tests import util


class RaveberryTest(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # https://stackoverflow.com/questions/46530784/make-django-test-case-database-visible-to-celery/46564964#46564964
        cls.celery_worker = start_worker(app, perform_ping_check=False)
        cls.celery_worker.__enter__()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        cls.celery_worker.__exit__(None, None, None)

    def setUp(self):
        self.client = Client()
        # many tests need admin rights for setup or execution
        # they will drop privileges if necessary
        util.admin_login(self.client)
        redis.start()

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
        return self._poll_state("musiq-state", break_condition, timeout=timeout)

    def _poll_lights_state(self, break_condition, timeout=1):
        return self._poll_state("lights-state", break_condition, timeout=timeout)
