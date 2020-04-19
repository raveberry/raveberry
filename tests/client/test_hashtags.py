from bs4 import BeautifulSoup
from django.urls import reverse

from core.models import Tag
from tests.raveberry_test import RaveberryTest


class HashtagTests(RaveberryTest):
    def test_empty(self):
        self.assertFalse(Tag.objects.exists())

    def _get_random_hashtag(self):
        html = self.client.get(reverse("musiq")).content
        soup = BeautifulSoup(html, "html.parser")
        hashtag = soup.find("span", id="hashtag_text")
        return hashtag.text

    def test_hashtag(self):
        self.client.post(reverse("submit_hashtag"), {"hashtag": "#test"})
        self.assertEquals(self._get_random_hashtag(), "#test")

    def test_no_hashtag(self):
        self.client.post(reverse("submit_hashtag"), {"hashtag": "test"})
        self.assertEquals(self._get_random_hashtag(), "#test")

    def test_multiple(self):
        hashtags = ["#test" + str(i) for i in range(10)]
        for hashtag in hashtags:
            self.client.post(reverse("submit_hashtag"), {"hashtag": hashtag})
        for _ in range(10):
            self.assertTrue(self._get_random_hashtag() in hashtags)
