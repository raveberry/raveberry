"""This module handles all settings related to system configuration."""
from __future__ import annotations

import configparser
import os
import re
import shutil
import subprocess
from typing import Dict, Optional, Tuple

import cachetools.func
import redis.exceptions
import requests
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseBadRequest

from core.musiq.playback import player_lock
from core.settings import storage
from core.settings.settings import control


def _restart_mopidy() -> None:
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/restart_mopidy"])
    try:
        player_lock.release()
    except redis.exceptions.LockError:
        # the lock was already released
        pass


def update_mopidy_config(output: str) -> None:
    """Updates mopidy's config with the credentials stored in the database.
    If no config_file is given, the default one is used."""
    if settings.DOCKER:
        # raveberry cannot restart mopidy in the docker setup
        return

    if output == "pulse":
        if storage.get("feed_cava") and shutil.which("cava"):
            output = "cava"
        else:
            output = "regular"

    spotify_username = storage.get("spotify_username")
    spotify_password = storage.get("spotify_password")
    spotify_client_id = storage.get("spotify_client_id")
    spotify_client_secret = storage.get("spotify_client_secret")
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
    _restart_mopidy()


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

    extensions = {}
    for line in log.split("\n")[::-1]:
        if "spotify" not in extensions:

            if (
                line.startswith("ERROR")
                and "spotify.session" in line
                and "USER_NEEDS_PREMIUM"
            ):
                extensions["spotify"] = (False, "Spotify Premium is required")
            elif line.startswith("ERROR") and "spotify.session" in line:
                extensions["spotify"] = (False, "User or Password are wrong")
            elif line.startswith("ERROR") and "mopidy_spotify.web" in line:
                extensions["spotify"] = (
                    False,
                    "Client ID or Client Secret are wrong or expired",
                )
            elif (
                line.startswith("WARNING")
                and "spotify" in line
                and "The extension has been automatically disabled" in line
            ):
                extensions["spotify"] = (False, "Configuration Error")

        if "soundcloud" not in extensions:
            if line.startswith("ERROR") and 'Invalid "auth_token"' in line:
                extensions["soundcloud"] = (False, "auth_token is invalid")
            elif (
                line.startswith("WARNING")
                and "soundcloud" in line
                and "The extension has been automatically disabled" in line
            ):
                extensions["soundcloud"] = (False, "Configuration Error")

        if "jamendo" not in extensions:
            if line.startswith("ERROR") and 'Invalid "client_id"' in line:
                extensions["jamendo"] = (False, "client_id is invalid")
            elif (
                line.startswith("WARNING")
                and "jamendo" in line
                and "The extension has been automatically disabled" in line
            ):
                extensions["jamendo"] = (False, "Configuration Error")

        if (
            "spotify" in extensions
            and "soundcloud" in extensions
            and "jamendo" in extensions
        ):
            break

        if line.startswith("Started Mopidy music server."):
            if "spotify" not in extensions:
                extensions["spotify"] = (True, "Login successful")
            if "soundcloud" not in extensions:
                extensions["soundcloud"] = (True, "auth_token valid")
            if "jamendo" not in extensions:
                extensions["jamendo"] = (True, "client_id could not be checked")
            break
    else:
        # there were too many lines in the log, could not determine whether there was an error
        if "spotify" not in extensions:
            extensions["spotify"] = (True, "No info found, enabling to be safe")
        if "soundcloud" not in extensions:
            extensions["soundcloud"] = (True, "No info found, enabling to be safe")
        if "jamendo" not in extensions:
            extensions["jamendo"] = (True, "No info found, enabling to be safe")
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
def restart_server(_request: WSGIRequest) -> None:
    """Restarts the server."""
    subprocess.call(["sudo", "/usr/local/sbin/raveberry/restart_server"])


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
    # https://github.com/pypa/pip/issues/9139
    p = subprocess.run(
        "pip3 install --use-deprecated=legacy-resolver raveberry==nonexistingversion".split(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if p.returncode == 2:
        # pip does not now the --use-deprecated=legacy-resolver
        # probably an older version that does not need it
        p = subprocess.run(
            "pip3 install raveberry==nonexistingversion".split(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

    # parse the newest verson from pip output
    for line in p.stderr.splitlines():
        if "from versions" in line:
            versions = [re.sub(r"[^0-9.]", "", token) for token in line.split()]
            versions = [version for version in versions if version]
            latest_version = versions[-1]
            return latest_version
    else:
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
    with open(os.path.join(settings.BASE_DIR, "config/raveberry.yaml")) as f:
        config = f.read()
    lines = config.splitlines()
    lines = [line for line in lines if not line.startswith("#")]
    return HttpResponse("\n".join(lines))


@control
def upgrade_raveberry(_request: WSGIRequest) -> HttpResponse:
    """Performs an upgrade of raveberry."""

    subprocess.call(["sudo", "/usr/local/sbin/raveberry/start_upgrade_service"])

    return HttpResponse("Upgrading... Look for logs in /var/www/")
