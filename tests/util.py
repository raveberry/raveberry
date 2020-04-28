import os
import pathlib
import urllib.request
import urllib.error

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse


def admin_login(client):
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "", "admin")
    client.login(username="admin", password="admin")


def download_test_library():
    test_library = os.path.join(settings.TEST_CACHE_DIR, "test_library")
    pathlib.Path(test_library).mkdir(parents=True, exist_ok=True)
    pathlib.Path(os.path.join(test_library, "Hard Rock")).mkdir(
        parents=True, exist_ok=True
    )
    pathlib.Path(os.path.join(test_library, "Techno")).mkdir(
        parents=True, exist_ok=True
    )

    hard_rock_filenames = [
        "ChecksForFree.mp3",
        "HeavyAction.mp3",
        "HiFiBrutality.mp3",
        "LongLiveDeath.mp3",
    ]
    techno_filenames = ["Sk8board.mp3", "TechTalk.mp3"]

    for filename in hard_rock_filenames:
        target_filename = os.path.join(
            os.path.join(test_library, "Hard Rock"), filename
        )
        if os.path.isfile(target_filename):
            continue
        try:
            urllib.request.urlretrieve(
                "https://audionautix.com/Music/" + filename, target_filename
            )
        except urllib.error.URLError:
            return False

    for filename in techno_filenames:
        target_filename = os.path.join(os.path.join(test_library, "Techno"), filename)
        if os.path.isfile(target_filename):
            continue
        try:
            urllib.request.urlretrieve(
                "https://audionautix.com/Music/" + filename, target_filename
            )
        except urllib.error.URLError:
            return False
    return True
