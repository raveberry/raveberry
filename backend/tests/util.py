import os
import pathlib
import urllib.request
import urllib.error

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


def admin_login(client: Client) -> None:
    user = get_user_model()
    if not user.objects.filter(username="admin").exists():
        user.objects.create_superuser("admin", "", "admin")
    client.login(username="admin", password="admin")


def download_test_library() -> bool:
    test_library = os.path.join(settings.TEST_CACHE_DIR, "test_library")
    pathlib.Path(test_library).mkdir(parents=True, exist_ok=True)
    pathlib.Path(os.path.join(test_library, "heroes")).mkdir(
        parents=True, exist_ok=True
    )
    pathlib.Path(os.path.join(test_library, "other")).mkdir(parents=True, exist_ok=True)

    heroes = ["Gothamlicious.mp3", "New Hero in Town.mp3"]
    other = ["Backbeat.mp3", "Forest Frolic Loop.mp3", "Village Tarantella.mp3"]

    for filename in heroes:
        target_filename = os.path.join(os.path.join(test_library, "heroes"), filename)
        if os.path.isfile(target_filename):
            continue
        try:
            urllib.request.urlretrieve(
                "https://freepd.com/music/" + filename.replace(" ", "%20"),
                target_filename,
            )
        except urllib.error.URLError:
            return False

    for filename in other:
        target_filename = os.path.join(os.path.join(test_library, "other"), filename)
        if os.path.isfile(target_filename):
            continue
        try:
            urllib.request.urlretrieve(
                "https://freepd.com/music/" + filename.replace(" ", "%20"),
                target_filename,
            )
        except urllib.error.URLError:
            return False
    return True
