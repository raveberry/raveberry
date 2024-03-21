"""This module handles all settings related to system configuration."""
from __future__ import annotations

import configparser
import os
import re
import shutil
import subprocess
import sys
from typing import Dict, Optional, Tuple

import cachetools.func
import requests
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseBadRequest

from core import redis
from core.settings import storage
from core.settings.settings import control


def restart_mopidy() -> None:
    """Restarts the mopidy systemd service."""
    from core.musiq.mopidy_player import mopidy_lock
    import redis.exceptions

    subprocess.call(["sudo", "/usr/local/sbin/raveberry/restart_mopidy"])
    try:
        mopidy_lock.release()
    except redis.exceptions.LockError:
        # the lock was already released
        pass


def update_mopidy_config(output: str) -> None:
    """Updates mopidy's config with the credentials stored in the database.
    If no config_file is given, the default one is used."""
    if settings.DOCKER:
        # raveberry cannot restart mopidy in the docker setup
        return

    if not redis.get("mopidy_available"):
        # mopidy can't be used if it is not available
        return

    if output == "pulse":
        if storage.get("feed_cava") and shutil.which("cava"):
            output = "cava"
        else:
            output = "regular"

    spotify_username = storage.get("spotify_username")
    spotify_password = storage.get("spotify_password")
    spotify_client_id = storage.get("spotify_mopidy_client_id")
    spotify_client_secret = storage.get("spotify_mopidy_client_secret")
    soundcloud_auth_token = storage.get("soundcloud_auth_token")
    jamendo_client_id = storage.get("jamendo_client_id")

    subprocess.call(
        [
            "sudo",
            "/usr/local/sbin/raveberry/update_mopidy_config",
            output,
            spotify_username,
            spotify_password,
            spotify_client_id,
            spotify_client_secret,
            soundcloud_auth_token,
            jamendo_client_id,
        ]
    )
    restart_mopidy()


def check_mopidy_extensions() -> Dict[str, Tuple[bool, str]]:
    """Returns a dict indicating for each extension whether it is enabled
    and provides a message.
    Handles both service and user mopidy instances."""
    try:
        subprocess.check_call(
            ["systemctl", "is-active", "mopidy"], stdout=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        extensions = _check_mopidy_extensions_user()
    else:
        extensions = _check_mopidy_extensions_service()
    return extensions


def _check_mopidy_extensions_user() -> Dict[str, Tuple[bool, str]]:
    config = subprocess.run(
        ["mopidy", "config"],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    ).stdout
    parser = configparser.ConfigParser()
    parser.read_string(config)
    extensions = {}
    for extension in ["spotify", "soundcloud", "jamendo"]:
        try:
            if parser[extension]["enabled"] == "true":
                extensions[extension] = (True, "Extension probably functional")
            else:
                extensions[extension] = (False, "Extension disabled")
        except KeyError:
            extensions[extension] = (False, "Extension disabled")
    return extensions


def _check_mopidy_extensions_service() -> Dict[str, Tuple[bool, str]]:
    # check the mopidy log and see if there is a spotify login error since the last restart
    log = subprocess.check_output(
        ["sudo", "/usr/local/sbin/raveberry/read_mopidy_log"], universal_newlines=True
    )

    # a dict that defines for each extension possible errors that can occur during mopidy start
    # for each error, there is a lambda that returns True if the error is present in a line
    # and a message that should be shown.
    error_handling = {
        "spotify": [
            (
                lambda line: line.startswith("ERROR")
                and "spotify.session" in line
                and "USER_NEEDS_PREMIUM" in line,
                "Spotify Premium is required",
            ),
            (
                lambda line: line.startswith("ERROR") and "spotify.session" in line,
                "User or Password are wrong",
            ),
            (
                lambda line: line.startswith("ERROR") and "mopidy_spotify.web" in line,
                "Client ID or Client Secret are wrong or expired",
            ),
            (
                lambda line: line.startswith("WARNING")
                and "spotify" in line
                and "The extension has been automatically disabled" in line,
                "Configuration Error",
            ),
        ],
        "soundcloud": [
            (
                lambda line: line.startswith("ERROR")
                and 'Invalid "auth_token"' in line,
                "auth_token is invalid",
            ),
            (
                lambda line: line.startswith("WARNING")
                and "soundcloud" in line
                and "The extension has been automatically disabled" in line,
                "Configuration Error",
            ),
        ],
        "jamendo": [
            (
                lambda line: line.startswith("ERROR") and 'Invalid "client_id"' in line,
                "client_id is invalid",
            )
        ],
    }
    success_messages = {
        "spotify": "Login successful",
        "soundcloud": "auth_token valid",
        "jamendo": "client_id could not be checked",
    }

    extensions = {}
    for line in log.split("\n")[::-1]:
        for extension in ["spotify", "soundcloud", "jamendo"]:
            # stop checking for errors if an error was already found for the extension
            if extension in extensions:
                continue
            for error_condition, error_message in error_handling[extension]:
                if error_condition(line):
                    extensions[extension] = (False, error_message)
            if (
                line.startswith("WARNING")
                and extension in line
                and "The extension has been automatically disabled" in line
            ):
                extensions[extension] = (False, "Configuration Error")

        if (
            "spotify" in extensions
            and "soundcloud" in extensions
            and "jamendo" in extensions
        ):
            break

        if line.startswith("Started Mopidy music server."):
            for extension in ["spotify", "soundcloud", "jamendo"]:
                if extension not in extensions:
                    extensions[extension] = (True, success_messages[extension])
            break
    for extension in ["spotify", "soundcloud", "jamendo"]:
        if extension not in extensions:
            # there were too many lines in the log, could not determine whether there was an error
            extensions[extension] = (True, "No info found, enabling to be safe")
    return extensions


@control
def disable_hotspot(_request: WSGIRequest) -> None:
    """Disable the wifi created by Raveberry."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_hotspot"])


@control
def enable_hotspot(_request: WSGIRequest) -> None:
    """Enable the wifi created by Raveberry."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_hotspot"])


@control
def disable_wifi_protection(_request: WSGIRequest) -> None:
    """Disable password protection of the hotspot, making it public."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_wifi_protection"])


@control
def enable_wifi_protection(_request: WSGIRequest) -> None:
    """Enable password protection of the hotspot.
    The password was defined during setup."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_wifi_protection"])


@control
def disable_tunneling(_request: WSGIRequest) -> None:
    """Disable forwarding of packets to the other network (probably the internet)."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_tunneling"])


@control
def enable_tunneling(_request: WSGIRequest) -> None:
    """Enable forwarding of packets to the other network.
    Enables clients connected to the hotspot to browse the internet (if available)."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_tunneling"])
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_tunneling"])


@control
def disable_remote(_request: WSGIRequest) -> None:
    """Disables the connection to an external server."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_remote"])


@control
def enable_remote(_request: WSGIRequest) -> None:
    """Enables the connection to an external server.
    Allows this instance to be reachable from a public domain."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_remote"])


@control
def disable_celery(_request: WSGIRequest) -> None:
    """Disables the use of celery and switches to using threads instead."""
    returncode = subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_celery"])
    if returncode == 1:
        # celery is already disabled
        return
    sys.exit(0)


@control
def enable_celery(_request: WSGIRequest) -> None:
    """Enables the use of celery for long running tasks."""
    returncode = subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_celery"])
    if returncode == 1:
        # celery is already enabled
        return
    sys.exit(0)


@control
def restart_server(_request: WSGIRequest) -> None:
    """Restarts the server."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/restart_server"])
    # if the restart was triggered from the web UI, the service is stuck on deactivating
    # exit this process to restart immediately
    sys.exit(0)


@control
def kill_workers(_request: WSGIRequest) -> None:
    """Force kills all celery workers."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/kill_workers"])


@control
def reboot_system(_request: WSGIRequest) -> None:
    """Reboots the system."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/reboot_system"])


@control
def shutdown_system(_request: WSGIRequest) -> None:
    """Shuts down the system."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/shutdown_system"])


@cachetools.func.ttl_cache(ttl=60 * 60 * 24)
def fetch_latest_version() -> Optional[str]:
    """Looks up the newest version number from PyPi and returns it."""
    if not redis.get("has_internet"):
        return None
    # https://github.com/pypa/pip/issues/9139
    # these subprocesses are expected to fail
    # move to pip index versions raveberry once that's not experimental anymore
    pip = subprocess.run(  # pylint: disable=subprocess-run-check
        "pip3 install --use-deprecated=legacy-resolver raveberry==nonexistingversion".split(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if pip.returncode == 2:
        # pip does not now the --use-deprecated=legacy-resolver
        # probably an older version that does not need it
        pip = subprocess.run(  # pylint: disable=subprocess-run-check
            "pip3 install raveberry==nonexistingversion".split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

    # parse the newest verson from pip output
    for line in pip.stderr.splitlines():
        if "from versions" in line:
            versions = [re.sub(r"[^0-9.]", "", token) for token in line.split()]
            versions = [version for version in versions if version]
            try:
                latest_version = versions[-1]
            except IndexError:
                return None
            return latest_version
    return None


@control
def get_latest_version(_request: WSGIRequest) -> HttpResponse:
    """Returns the newest version number of Raveberry from PyPi."""
    latest_version = fetch_latest_version()
    if latest_version is None:
        return HttpResponseBadRequest("Could not determine latest version.")
    return HttpResponse(latest_version)


@control
def get_changelog(_request: WSGIRequest) -> HttpResponse:
    """Retreives the changelog and returns it."""
    changelog = requests.get(
        "https://raw.githubusercontent.com/raveberry/raveberry/master/CHANGELOG.md"
    ).text
    return HttpResponse(changelog)


@control
def get_upgrade_config(_request: WSGIRequest) -> HttpResponse:
    """Returns the config that will be used for the upgrade."""
    with open(
        os.path.join(settings.BASE_DIR, "config/raveberry.yaml"), encoding="utf-8"
    ) as config_file:
        config = config_file.read()
    lines = config.splitlines()
    lines = [line for line in lines if not line.startswith("#")]
    return HttpResponse("\n".join(lines))


@control
def upgrade_raveberry(_request: WSGIRequest) -> HttpResponse:
    """Performs an upgrade of raveberry."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/start_upgrade_service"])
    return HttpResponse("Upgrading... Look for logs in /var/www/")
