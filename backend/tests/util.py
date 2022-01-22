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
    pathlib.Path(os.path.join(test_library, "ogg")).mkdir(parents=True, exist_ok=True)
    pathlib.Path(os.path.join(test_library, "mp3")).mkdir(parents=True, exist_ok=True)

    ogg_filenames = ["file_example_OOG_1MG.ogg", "file_example_OOG_2MG.ogg"]
    mp3_filenames = [
        "file_example_MP3_700KB.mp3",
        "file_example_MP3_1MG.mp3",
        "file_example_MP3_2MG.mp3",
    ]
    for filename in ogg_filenames:
        target_filename = os.path.join(os.path.join(test_library, "ogg"), filename)
        if os.path.isfile(target_filename):
            continue
        try:
            urllib.request.urlretrieve(
                "https://file-examples-com.github.io/uploads/2017/11/" + filename,
                target_filename,
            )
        except urllib.error.URLError:
            return False

    for filename in mp3_filenames:
        target_filename = os.path.join(os.path.join(test_library, "mp3"), filename)
        if os.path.isfile(target_filename):
            continue
        try:
            urllib.request.urlretrieve(
                "https://file-examples-com.github.io/uploads/2017/11/" + filename,
                target_filename,
            )
        except urllib.error.URLError:
            return False
    return True
