import colorsys
import json
import time
from threading import Thread
from unittest.mock import Mock

from django.db import connection
from django.urls import reverse

from core import redis
from core.lights.worker import DeviceManager
from tests.raveberry_test import RaveberryTest


class LedTests(RaveberryTest):
    def setUp(self):
        super().setUp()

        # similar to the playback thread in MusicTest
        # instead that here we need a reference to the manager object in order to introduce mocks
        # so we imitate the task

        self.manager = DeviceManager()
        self.manager.ring.initialized = True
        self.manager.strip.initialized = True
        self.set_ring_colors = Mock()
        self.set_strip_color = Mock()
        self.manager.ring.set_colors = self.set_ring_colors
        self.manager.ring.clear = Mock()
        self.manager.strip.set_color = self.set_strip_color
        self.manager.strip.clear = Mock()

        def _worker_thread():
            self.manager.loop()
            connection.close()

        self.worker_thread = Thread(target=_worker_thread)
        self.worker_thread.start()

    def tearDown(self):
        self.client.post(reverse("set-ring-program"), {"value": "Disabled"})
        self.client.post(reverse("set-strip-program"), {"value": "Disabled"})

        redis.publish("lights_settings_changed", "stop")
        self.worker_thread.join(timeout=10)

        super().tearDown()

    def test_fixed(self):
        self.client.post(reverse("set-ring-program"), {"value": "Fixed"})
        self.client.post(reverse("set-strip-program"), {"value": "Fixed"})
        time.sleep(0.5)
        self.set_ring_colors.assert_called_with(
            list((0, 0, 0) for _ in range(self.manager.ring.LED_COUNT))
        )
        self.set_strip_color.assert_called_with((0, 0, 0))
        self.client.post(reverse("set-fixed-color"), {"value": "#abcdef"})
        time.sleep(0.5)
        color = tuple(val / 255 for val in (0xAB, 0xCD, 0xEF))
        self.set_ring_colors.assert_called_with(
            list(color for _ in range(self.manager.ring.LED_COUNT))
        )
        self.set_strip_color.assert_called_with(color)

    def _assert_all_hues(self, colors):
        hues = []
        for color in colors:
            hue, _, _ = colorsys.rgb_to_hsv(*color)
            hues.append(hue)

        for target_hue in range(0, 10):
            closest = min(abs(hue - target_hue / 10) for hue in hues)
            self.assertLess(closest, 0.1)

    def test_rainbow(self):
        self.client.post(reverse("set-ring-program"), {"value": "Rainbow"})
        self.client.post(reverse("set-strip-program"), {"value": "Rainbow"})
        self.client.post(reverse("set-program-speed"), {"value": "2"})
        time.sleep(0.5)

        # make sure all colors of the rainbow were shown
        strip_colors = [args[0] for args, _ in self.set_strip_color.call_args_list]
        self._assert_all_hues(strip_colors)

        # make sure the ring shows all colors every frame
        ring_colors = [args[0] for args, _ in self.set_ring_colors.call_args_list]
        for frame in ring_colors:
            self._assert_all_hues(frame)

    def test_shortcut(self):
        self.client.post(reverse("set-ring-program"), {"value": "Fixed"})
        self.client.post(reverse("set-strip-program"), {"value": "Rainbow"})

        self.client.post(reverse("set-ring-program"), {"value": "Disabled"})
        self.client.post(reverse("set-strip-program"), {"value": "Disabled"})

        state = json.loads(self.client.get(reverse("lights-state")).content)
        self.assertFalse(state["lightsEnabled"])

        self.client.post(reverse("set-lights-shortcut"), {"value": "true"})

        state = json.loads(self.client.get(reverse("lights-state")).content)
        self.assertEqual(state["lights"]["ringProgram"], "Fixed")
        self.assertEqual(state["lights"]["stripProgram"], "Rainbow")
