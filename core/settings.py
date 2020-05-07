"""This module contains everything related to the settings and configuration of the server."""
# pylint: disable=no-self-use  # self is used in decorator

from __future__ import annotations

import configparser
import logging
import math
import os
import re
import shutil
import socket
import subprocess
import time
from datetime import timedelta
from functools import wraps
from typing import Callable, Dict, Any, TYPE_CHECKING, Optional, List

from dateutil import tz
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.handlers.wsgi import WSGIRequest
from django.db import models
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import dateparse
from django.utils import timezone
from mutagen import MutagenError

import core.musiq.song_utils as song_utils
from core.models import PlayLog
from core.models import RequestLog
from core.models import Setting, ArchivedSong, ArchivedPlaylist, PlaylistEntry
from core.state_handler import Stateful
from core.util import background_thread

if TYPE_CHECKING:
    from core.base import Base


def option(
    func: Callable[["Settings", WSGIRequest], Optional[HttpResponse]]
) -> Callable[["Settings", WSGIRequest], HttpResponse]:
    """A decorator that makes sure that only the admin changes a setting."""

    def _decorator(self: "Settings", request: WSGIRequest) -> HttpResponse:
        # don't allow option changes during alarm
        if request.user.username != "admin":
            return HttpResponseForbidden()
        response = func(self, request)
        self.update_state()
        if response is not None:
            return response
        return HttpResponse()

    return wraps(func)(_decorator)


class Settings(Stateful):
    """This class is responsible for handling requests from the /settings page."""

    @staticmethod
    def get_setting(key: str, default: str) -> str:
        """This method returns the value for the given :param key:.
        Vaules of non-existing keys are set to :param default:"""
        return Setting.objects.get_or_create(key=key, defaults={"value": default})[
            0
        ].value

    @staticmethod
    def _get_mopidy_config() -> str:
        if shutil.which("cava"):
            # if cava is installed, use the visualization config for mopidy
            config_file = os.path.join(settings.BASE_DIR, "setup/mopidy_cava.conf")
        else:
            config_file = os.path.join(settings.BASE_DIR, "setup/mopidy.conf")
        return config_file

    def __init__(self, base: "Base") -> None:
        self.base = base
        self.voting_system = self.get_setting("voting_system", "False") == "True"
        self.logging_enabled = self.get_setting("logging_enabled", "True") == "True"
        self.people_to_party = int(self.get_setting("people_to_party", "3"))
        self.alarm_probability = float(self.get_setting("alarm_probability", "0"))
        self.downvotes_to_kick = int(self.get_setting("downvotes_to_kick", "3"))
        self.max_download_size = int(self.get_setting("max_download_size", "10"))
        self.max_playlist_items = int(self.get_setting("max_playlist_items", "10"))
        self.youtube_enabled = self.get_setting("youtube_enabled", "True") == "True"
        self.spotify_username = self.get_setting("spotify_username", "")
        self.spotify_password = self.get_setting("spotify_password", "")
        self.spotify_client_id = self.get_setting("spotify_client_id", "")
        self.spotify_client_secret = self.get_setting("spotify_client_secret", "")

        self.spotify_enabled = False
        self._check_spotify()
        self._check_internet()
        self.bluetoothctl: Optional[subprocess.Popen[bytes]] = None
        self.bluetooth_devices: List[Dict[str, str]] = []
        self.homewifi = self.get_setting("homewifi", "")
        self.scan_progress = "0 / 0 / 0"

    def state_dict(self) -> Dict[str, Any]:
        state_dict = self.base.state_dict()
        state_dict["voting_system"] = self.voting_system
        state_dict["logging_enabled"] = self.logging_enabled
        state_dict["people_to_party"] = self.people_to_party
        state_dict["alarm_probability"] = self.alarm_probability
        state_dict["downvotes_to_kick"] = self.downvotes_to_kick
        state_dict["max_download_size"] = self.max_download_size
        state_dict["max_playlist_items"] = self.max_playlist_items
        state_dict["has_internet"] = self.has_internet

        state_dict["youtube_enabled"] = self.youtube_enabled

        state_dict["spotify_credentials_valid"] = self.spotify_enabled

        state_dict["bluetooth_scanning"] = self.bluetoothctl is not None
        state_dict["bluetooth_devices"] = self.bluetooth_devices

        try:
            with open(os.path.join(settings.BASE_DIR, "config/homewifi")) as f:
                state_dict["homewifi_ssid"] = f.read()
        except FileNotFoundError:
            state_dict["homewifi_ssid"] = ""

        state_dict["scan_progress"] = self.scan_progress

        if settings.DOCKER and not settings.DOCKER_ICECAST:
            # icecast is definitely disabled
            streaming_enabled = False
        else:
            # the icecast service reports as active even if it is internally disabled.
            # check if its port is used to determine if it's running
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                streaming_enabled = s.connect_ex((settings.ICECAST_HOST, 8000)) == 0
        state_dict["streaming_enabled"] = streaming_enabled

        try:
            state_dict["homewifi_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/homewifi_enabled"]) != 0
            )
            state_dict["events_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/events_enabled"]) != 0
            )
            state_dict["hotspot_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/hotspot_enabled"]) != 0
            )
            state_dict["wifi_protected"] = (
                subprocess.call(["/usr/local/sbin/raveberry/wifi_protected"]) != 0
            )
            state_dict["tunneling_enabled"] = (
                subprocess.call(["sudo", "/usr/local/sbin/raveberry/tunneling_enabled"])
                != 0
            )
            state_dict["remote_enabled"] = (
                subprocess.call(["/usr/local/sbin/raveberry/remote_enabled"]) != 0
            )
        except FileNotFoundError:
            logging.info("scripts not installed")

        return state_dict

    def index(self, request: WSGIRequest) -> HttpResponse:
        """Renders the /settings page. Only admin is allowed to see this page."""
        if not self.base.user_manager.is_admin(request.user):
            raise PermissionDenied
        context = self.base.context(request)
        return render(request, "settings.html", context)

    def _update_mopidy_config(self, config_file) -> None:
        subprocess.call(
            [
                "sudo",
                "/usr/local/sbin/raveberry/update_mopidy_config",
                config_file,
                self.spotify_username,
                self.spotify_password,
                self.spotify_client_id,
                self.spotify_client_secret,
            ]
        )
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/restart_mopidy"])

    def _check_spotify(self, credentials_changed: bool = False) -> HttpResponse:
        if not self.spotify_client_id or not self.spotify_client_secret:
            self.spotify_enabled = False
            return HttpResponseBadRequest("Not all credentials provided")
        if settings.DOCKER:
            self.spotify_enabled = True
            return HttpResponse(
                "Make sure to set mopidy config with spotify credentials."
            )
        try:
            subprocess.check_call(
                ["systemctl", "is-active", "mopidy"], stdout=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            return self._check_spotify_user()
        return self._check_spotify_service(credentials_changed=credentials_changed)

    def _check_spotify_user(self) -> HttpResponse:
        self.spotify_enabled = False
        config = subprocess.run(
            ["mopidy", "config"],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            check=True,
        ).stdout
        parser = configparser.ConfigParser()
        parser.read_string(config)
        try:
            if parser["spotify"]["enabled"] == "true":
                self.spotify_enabled = True
                return HttpResponse("Login probably successful")
        except KeyError:
            pass
        return HttpResponseBadRequest("Config is invalid")

    def _check_spotify_service(self, credentials_changed: bool = False) -> HttpResponse:
        if credentials_changed:
            config_file = self._get_mopidy_config()
            self._update_mopidy_config(config_file)

            # wait for mopidy to try spotify login
            time.sleep(5)

        # check the mopidy log and see if there is a spotify login error since the last restart
        log = subprocess.check_output(
            ["sudo", "/usr/local/sbin/raveberry/read_mopidy_log"],
            universal_newlines=True,
        )
        login_error = False
        response: HttpResponse
        for line in log.split("\n")[::-1]:
            if line.startswith("ERROR") and "spotify.session" in line:
                login_error = True
                response = HttpResponseBadRequest("User or Password are wrong")
                break
            if line.startswith("ERROR") and "mopidy_spotify.web" in line:
                login_error = True
                response = HttpResponseBadRequest(
                    "Client ID or Client Secret are wrong or expired"
                )
                break
            if (
                line.startswith("WARNING")
                and "The extension has been automatically disabled" in line
            ):
                login_error = True
                response = HttpResponseBadRequest("Configuration Error")
                break
            if line.startswith("Started Mopidy music server."):
                response = HttpResponse("Login successful")
                break
        else:
            # there were too many lines in the log, could not determine whether there was an error
            # leave spotify_enabled status as it is
            return HttpResponseBadRequest("Could not check credentials")

        if not login_error:
            self.spotify_enabled = True
        else:
            self.spotify_enabled = False
        return response

    def _check_internet(self) -> None:
        response = subprocess.call(
            ["ping", "-c", "1", "-W", "3", "1.1.1.1"], stdout=subprocess.DEVNULL
        )
        if response == 0:
            self.has_internet = True
        else:
            self.has_internet = False

    @option
    def set_voting_system(self, request: WSGIRequest) -> None:
        """Enables or disables the voting system based on the given value."""
        enabled = request.POST.get("value") == "true"
        Setting.objects.filter(key="voting_system").update(value=enabled)
        self.voting_system = enabled

    @option
    def set_logging_enabled(self, request: WSGIRequest) -> None:
        """Enables or disables logging of requests and play logs based on the given value."""
        enabled = request.POST.get("value") == "true"
        Setting.objects.filter(key="logging_enabled").update(value=enabled)
        self.logging_enabled = enabled

    @option
    def set_people_to_party(self, request: WSGIRequest) -> None:
        """Sets the amount of active clients needed to enable partymode."""
        value = int(request.POST.get("value"))  # type: ignore
        Setting.objects.filter(key="people_to_party").update(value=value)
        self.people_to_party = value

    @option
    def set_alarm_probability(self, request: WSGIRequest) -> None:
        """Sets the probability with which an alarm is triggered after each song."""
        value = float(request.POST.get("value"))  # type: ignore
        Setting.objects.filter(key="alarm_probability").update(value=value)
        self.alarm_probability = value

    @option
    def set_downvotes_to_kick(self, request: WSGIRequest) -> None:
        """Sets the number of downvotes that are needed to remove a song from the queue."""
        value = int(request.POST.get("value"))  # type: ignore
        Setting.objects.filter(key="downvotes_to_kick").update(value=value)
        self.downvotes_to_kick = value

    @option
    def set_max_download_size(self, request: WSGIRequest) -> None:
        """Sets the maximum amount of MB that are allowed for a song that needs to be downloaded."""
        value = int(request.POST.get("value"))  # type: ignore
        Setting.objects.filter(key="max_download_size").update(value=value)
        self.max_download_size = value

    @option
    def set_max_playlist_items(self, request: WSGIRequest) -> None:
        """Sets the maximum number of songs that are downloaded from a playlist."""
        value = int(request.POST.get("value"))  # type: ignore
        Setting.objects.filter(key="max_playlist_items").update(value=value)
        self.max_playlist_items = value

    @option
    def check_internet(self, _request: WSGIRequest) -> None:
        """Checks whether an internet connection exists and updates the internal state."""
        self._check_internet()

    @option
    def update_user_count(self, _request: WSGIRequest) -> None:
        """Force an update on the active user count."""
        self.base.user_manager.update_user_count()

    @option
    def check_spotify_credentials(self, _request: WSGIRequest) -> HttpResponse:
        """Check whether the provided credentials are valid."""
        return self._check_spotify()

    @option
    def set_youtube_enabled(self, request: WSGIRequest):
        """Enables or disables youtube to be used as a song provider."""
        enabled = request.POST.get("value") == "true"
        Setting.objects.filter(key="youtube_enabled").update(value=enabled)
        self.youtube_enabled = enabled

    @option
    def set_spotify_credentials(self, request: WSGIRequest) -> HttpResponse:
        """Update spotify credentials."""
        username = request.POST.get("username")
        password = request.POST.get("password")
        client_id = request.POST.get("client_id")
        client_secret = request.POST.get("client_secret")

        if not username or not password or not client_id or not client_secret:
            return HttpResponseBadRequest("All fields are required")

        self.spotify_username = username
        self.spotify_password = password
        self.spotify_client_id = client_id
        self.spotify_client_secret = client_secret

        Setting.objects.filter(key="spotify_username").update(
            value=self.spotify_username
        )
        Setting.objects.filter(key="spotify_password").update(
            value=self.spotify_password
        )
        Setting.objects.filter(key="spotify_client_id").update(
            value=self.spotify_client_id
        )
        Setting.objects.filter(key="spotify_client_secret").update(
            value=self.spotify_client_secret
        )

        return self._check_spotify(credentials_changed=True)

    def _get_bluetoothctl_line(self) -> str:
        # Note: this variable is not guarded by a lock.
        # But there should only be one admin accessing these bluetooth functions anyway.
        if self.bluetoothctl is None:
            return ""
        assert self.bluetoothctl.stdout
        line = self.bluetoothctl.stdout.readline().decode()
        ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        line = ansi_escape.sub("", line)
        line = line.strip()
        return line

    def _stop_bluetoothctl(self) -> None:
        if self.bluetoothctl:
            assert self.bluetoothctl.stdin
            self.bluetoothctl.stdin.close()
            self.bluetoothctl.wait()
        self.bluetoothctl = None

    @option
    def set_bluetooth_scanning(self, request: WSGIRequest) -> HttpResponse:
        """Enables scanning of bluetooth devices."""
        enabled = request.POST.get("value") == "true"
        if enabled:
            if self.bluetoothctl is not None:
                return HttpResponseBadRequest("Already Scanning")
            self.bluetooth_devices = []
            self.bluetoothctl = subprocess.Popen(
                ["bluetoothctl"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )
            assert self.bluetoothctl.stdin

            self.bluetoothctl.stdin.write(b"devices\n")
            self.bluetoothctl.stdin.write(b"scan on\n")
            self.bluetoothctl.stdin.flush()
            while True:
                line = self._get_bluetoothctl_line()
                if not line:
                    break
                # match old devices
                match = re.match(r"Device (\S*) (.*)", line)
                # match newly scanned devices
                # We need the '.*' at the beginning of the line to account for control sequences
                if not match:
                    match = re.match(r".*\[NEW\] Device (\S*) (.*)", line)
                if match:
                    address = match.group(1)
                    name = match.group(2)
                    # filter unnamed devices
                    # devices named after their address are no speakers
                    if re.match("[A-Z0-9][A-Z0-9](-[A-Z0-9][A-Z0-9]){5}", name):
                        continue
                    self.bluetooth_devices.append({"address": address, "name": name})
                    self.update_state()
        else:
            if self.bluetoothctl is None:
                return HttpResponseBadRequest("Currently not scanning")
            self._stop_bluetoothctl()
        return HttpResponse()

    @option
    def connect_bluetooth(self, request: WSGIRequest) -> HttpResponse:
        """Connect to a given bluetooth device."""
        address = request.POST.get("address")
        if self.bluetoothctl is not None:
            return HttpResponseBadRequest("Stop scanning before connecting")
        if address is None or address == "":
            return HttpResponseBadRequest("No device selected")

        self.bluetoothctl = subprocess.Popen(
            ["bluetoothctl"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
        assert self.bluetoothctl.stdin
        error = ""

        # A Function that acts as a timeout for unexpected errors (or timeouts)
        @background_thread
        def _timeout() -> None:
            nonlocal error
            time.sleep(20)
            error = "Timed out"
            if self.bluetoothctl is not None:
                self._stop_bluetoothctl()

        self.bluetoothctl.stdin.write(b"pair " + address.encode() + b"\n")
        self.bluetoothctl.stdin.flush()
        while True:
            line = self._get_bluetoothctl_line()
            if not line:
                break
            if re.match(".*Device " + address + " not available", line):
                error = "Device unavailable"
                break
            if re.match(".*Failed to pair: org.bluez.Error.AlreadyExists", line):
                break
            if re.match(".*Pairing successful", line):
                break

        if error:
            self._stop_bluetoothctl()
            return HttpResponseBadRequest(error)

        self.bluetoothctl.stdin.write(b"connect " + address.encode() + b"\n")
        self.bluetoothctl.stdin.flush()
        while True:
            line = self._get_bluetoothctl_line()
            if not line:
                break
            if re.match(".*Device " + address + " not available", line):
                error = "Device unavailable"
                break
            if re.match(".*Failed to connect: org.bluez.Error.Failed", line):
                error = "Connect Failed"
                break
            if re.match(".*Failed to connect: org.bluez.Error.InProgress", line):
                error = "Connect in progress"
                break
            if re.match(".*Connection successful", line):
                break
        # trust the device to automatically reconnect when it is available again
        self.bluetoothctl.stdin.write(b"trust " + address.encode() + b"\n")
        self.bluetoothctl.stdin.flush()

        self._stop_bluetoothctl()
        if error:
            return HttpResponseBadRequest(error)

        # parse the sink number of the bluetooth device from pactl
        sinks = subprocess.check_output(
            "pactl list short sinks".split(), universal_newlines=True
        )
        bluetooth_sink = "2"
        for sink in sinks.split("\n"):
            if "bluez" in sink:
                bluetooth_sink = sink[0]
                break
        subprocess.call(
            f"pactl set-default-sink {bluetooth_sink}".split(),
            stdout=subprocess.DEVNULL,
        )
        # restart mopidy to apply audio device change
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/restart_mopidy"])

        return HttpResponse("Connected")

    @option
    def disconnect_bluetooth(self, _request: WSGIRequest) -> HttpResponse:
        """Disconnect from the current bluetooth device."""
        subprocess.call("pactl set-default-sink 0".split(), stdout=subprocess.DEVNULL)
        # restart mopidy to apply audio device change
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/restart_mopidy"])
        return HttpResponse("Disconnected")

    @option
    def available_ssids(self, _request: WSGIRequest) -> JsonResponse:
        """List all ssids that can currently be seen."""
        output = subprocess.check_output(
            ["sudo", "/usr/local/sbin/raveberry/list_available_ssids"]
        ).decode()
        ssids = output.split("\n")
        return JsonResponse(ssids[:-1], safe=False)

    @option
    def connect_to_wifi(self, request: WSGIRequest) -> HttpResponse:
        """Connect to a given ssid with the given password."""
        ssid = request.POST.get("ssid")
        password = request.POST.get("password")
        if ssid is None or password is None or ssid == "" or password == "":
            return HttpResponseBadRequest("Please provide both SSID and password")
        try:
            output = subprocess.check_output(
                ["sudo", "/usr/local/sbin/raveberry/connect_to_wifi", ssid, password]
            ).decode()
            return HttpResponse(output)
        except subprocess.CalledProcessError as e:
            output = e.output.decode()
            return HttpResponseBadRequest(output)

    @option
    def disable_homewifi(self, _request: WSGIRequest) -> None:
        """Disable homewifi function."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_homewifi"])

    @option
    def enable_homewifi(self, _request: WSGIRequest) -> None:
        """Enable homewifi function."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_homewifi"])

    @option
    def stored_ssids(self, _request: WSGIRequest) -> JsonResponse:
        """Return the list of ssids that this Raspberry Pi was connected to in the past."""
        output = subprocess.check_output(
            ["sudo", "/usr/local/sbin/raveberry/list_stored_ssids"]
        ).decode()
        ssids = output.split("\n")
        return JsonResponse(ssids[:-1], safe=False)

    @option
    def set_homewifi_ssid(self, request: WSGIRequest) -> HttpResponse:
        """Set the home network.
        The hotspot will not be created if connected to this wifi."""
        homewifi_ssid = request.POST.get("homewifi_ssid")
        if homewifi_ssid is None:
            return HttpResponseBadRequest("homewifi ssid was not supplied.")
        with open(os.path.join(settings.BASE_DIR, "config/homewifi"), "w+") as f:
            f.write(homewifi_ssid)
        return HttpResponse()

    @option
    def list_subdirectories(self, request: WSGIRequest) -> HttpResponse:
        """Returns a list of all subdirectories for the given path."""
        path = request.GET.get("path")
        if path is None:
            return HttpResponseBadRequest("path was not supplied.")
        basedir, subdirpart = os.path.split(path)
        if path == "":
            suggestions = ["/"]
        elif os.path.isdir(basedir):
            suggestions = [
                os.path.join(basedir, subdir + "/")
                for subdir in next(os.walk(basedir))[1]
                if subdir.lower().startswith(subdirpart.lower())
            ]
            suggestions.sort()
        else:
            suggestions = ["not a valid directory"]
        if not suggestions:
            suggestions = ["not a valid directory"]
        return JsonResponse(suggestions, safe=False)

    @option
    def scan_library(self, request: WSGIRequest) -> HttpResponse:
        """Scan the folder at the given path and add all its sound files to the database."""
        library_path = request.POST.get("library_path")
        if library_path is None:
            return HttpResponseBadRequest("library path was not supplied.")

        if not os.path.isdir(library_path):
            return HttpResponseBadRequest("not a directory")
        library_path = os.path.abspath(library_path)

        self.scan_progress = "0 / 0 / 0"
        self.update_state()

        self._scan_library(library_path)

        return HttpResponse(
            f"started scanning in {library_path}. This could take a while"
        )

    @background_thread
    def _scan_library(self, library_path: str) -> None:
        scan_start = time.time()
        last_update = scan_start
        update_frequency = 0.5
        filecount = 0
        for (dirpath, _, filenames) in os.walk(library_path):
            now = time.time()
            if now - last_update > update_frequency:
                last_update = now
                self.scan_progress = f"{filecount} / 0 / 0"
                self.update_state()
            if os.path.abspath(dirpath) == os.path.abspath(settings.SONGS_CACHE_DIR):
                # do not add files handled by raveberry as local files
                continue
            filecount += len(filenames)

        library_link = os.path.join(settings.SONGS_CACHE_DIR, "local_library")
        try:
            os.remove(library_link)
        except FileNotFoundError:
            pass
        os.symlink(library_path, library_link)

        logging.info(f"started scanning in {library_path}")

        self.scan_progress = f"{filecount} / 0 / 0"
        self.update_state()

        files_scanned = 0
        files_added = 0
        for (dirpath, _, filenames) in os.walk(library_path):
            if os.path.abspath(dirpath) == os.path.abspath(settings.SONGS_CACHE_DIR):
                # do not add files handled by raveberry as local files
                continue
            now = time.time()
            if now - last_update > update_frequency:
                last_update = now
                self.scan_progress = f"{filecount} / {files_scanned} / {files_added}"
                self.update_state()
            for filename in filenames:
                files_scanned += 1
                path = os.path.join(dirpath, filename)
                try:
                    metadata = song_utils.get_metadata(path)
                except (ValueError, MutagenError):
                    # the given file could not be parsed and will not be added to the database
                    pass
                else:
                    library_relative_path = path[len(library_path) + 1 :]
                    external_url = os.path.join("local_library", library_relative_path)
                    if not ArchivedSong.objects.filter(url=external_url).exists():
                        files_added += 1
                        ArchivedSong.objects.create(
                            url=external_url,
                            artist=metadata["artist"],
                            title=metadata["title"],
                            counter=0,
                        )

        assert files_scanned == filecount
        self.scan_progress = f"{filecount} / {files_scanned} / {files_added}"
        self.update_state()

        logging.info(f"done scanning in {library_path}")

    @option
    def create_playlists(self, _request: WSGIRequest) -> HttpResponse:
        """Create a playlist for every folder in the library."""
        library_link = os.path.join(settings.SONGS_CACHE_DIR, "local_library")
        if not os.path.islink(library_link):
            return HttpResponseBadRequest("No library set")

        self.scan_progress = f"0 / 0 / 0"
        self.update_state()

        self._create_playlists()

        return HttpResponse(f"started creating playlsts. This could take a while")

    @background_thread
    def _create_playlists(self) -> None:
        local_files = ArchivedSong.objects.filter(
            url__startswith="local_library"
        ).count()

        library_link = os.path.join(settings.SONGS_CACHE_DIR, "local_library")
        library_path = os.path.abspath(library_link)

        logging.info(f"started creating playlists in {library_path}")

        self.scan_progress = f"{local_files} / 0 / 0"
        self.update_state()

        scan_start = time.time()
        last_update = scan_start
        update_frequency = 0.5
        files_processed = 0
        files_added = 0
        for (dirpath, _, filenames) in os.walk(library_path):
            now = time.time()
            if now - last_update > update_frequency:
                last_update = now
                self.scan_progress = (
                    f"{local_files} / {files_processed} / {files_added}"
                )
                self.update_state()

            song_urls = []
            # unfortunately there is no way to access track numbers accross different file types
            # so we have to add songs to playlists alphabetically
            for filename in sorted(filenames):
                path = os.path.join(dirpath, filename)
                library_relative_path = path[len(library_path) + 1 :]
                external_url = os.path.join("local_library", library_relative_path)
                if ArchivedSong.objects.filter(url=external_url).exists():
                    files_processed += 1
                    song_urls.append(external_url)

            if not song_urls:
                continue

            playlist_id = os.path.join(
                "local_library", dirpath[len(library_path) + 1 :]
            )
            playlist_title = os.path.split(dirpath)[1]
            playlist, created = ArchivedPlaylist.objects.get_or_create(
                list_id=playlist_id, title=playlist_title, counter=0
            )
            if not created:
                # this playlist already exists, skip
                continue

            song_index = 0
            for external_url in song_urls:
                PlaylistEntry.objects.create(
                    playlist=playlist, index=song_index, url=external_url,
                )
                files_added += 1
                song_index += 1

        self.scan_progress = f"{local_files} / {files_processed} / {files_added}"
        self.update_state()

        logging.info(f"finished creating playlists in {library_path}")

    @option
    def analyse(self, request: WSGIRequest) -> HttpResponse:
        """Perform an analysis of the database in the given timeframe."""
        startdate = request.POST.get("startdate")
        starttime = request.POST.get("starttime")
        enddate = request.POST.get("enddate")
        endtime = request.POST.get("endtime")
        if not startdate or not starttime or not enddate or not endtime:
            return HttpResponseBadRequest("All fields are required")

        start = dateparse.parse_datetime(startdate + "T" + starttime)
        end = dateparse.parse_datetime(enddate + "T" + endtime)

        if start is None or end is None:
            return HttpResponseBadRequest("invalid start-/endtime given")
        if start >= end:
            return HttpResponseBadRequest("start has to be before end")

        start = timezone.make_aware(start)
        end = timezone.make_aware(end)

        played = (
            PlayLog.objects.all().filter(created__gte=start).filter(created__lt=end)
        )
        requested = (
            RequestLog.objects.all().filter(created__gte=start).filter(created__lt=end)
        )
        played_count = (
            played.values("song__url", "song__artist", "song__title")
            .values(
                "song__url",
                "song__artist",
                "song__title",
                count=models.Count("song__url"),
            )
            .order_by("-count")
        )
        played_votes = (
            PlayLog.objects.all()
            .filter(created__gte=start)
            .filter(created__lt=end)
            .order_by("-votes")
        )
        devices = requested.values("address").values(
            "address", count=models.Count("address")
        )

        response = {
            "songs_played": len(played),
            "most_played_song": (
                song_utils.displayname(
                    played_count[0]["song__artist"], played_count[0]["song__title"]
                )
                + f" ({played_count[0]['count']})"
            ),
            "highest_voted_song": (
                played_votes[0].song_displayname() + f" ({played_votes[0].votes})"
            ),
            "most_active_device": (devices[0]["address"] + f" ({devices[0]['count']})"),
        }
        requested_by_ip = requested.filter(address=devices[0]["address"])
        for i in range(6):
            if i >= len(requested_by_ip):
                break
            response["most_active_device"] += "\n"
            if i == 5:
                response["most_active_device"] += "..."
            else:
                response["most_active_device"] += requested_by_ip[i].item_displayname()

        binsize = 3600
        number_of_bins = math.ceil((end - start).total_seconds() / binsize)
        request_bins = [0 for _ in range(number_of_bins)]

        for request_log in requested:
            seconds = (request_log.created - start).total_seconds()
            index = int(seconds / binsize)
            request_bins[index] += 1

        current_time = start
        current_index = 0
        response["request_activity"] = ""
        while current_time < end:
            response["request_activity"] += current_time.strftime("%H:%M")
            response["request_activity"] += ":\t" + str(request_bins[current_index])
            response["request_activity"] += "\n"
            current_time += timedelta(seconds=binsize)
            current_index += 1

        localtz = tz.gettz(settings.TIME_ZONE)
        playlist = ""
        for play_log in played:
            localtime = play_log.created.astimezone(localtz)
            playlist += "[{:02d}:{:02d}] {}\n".format(
                localtime.hour, localtime.minute, play_log.song_displayname()
            )
        response["playlist"] = playlist

        return JsonResponse(response)

    @option
    def enable_streaming(self, _request: WSGIRequest) -> HttpResponse:
        """Enable icecast streaming."""
        if settings.DOCKER:
            return HttpResponseBadRequest(
                "Choose the correct docker-compose file to control streaming"
            )

        icecast_exists = False
        for line in subprocess.check_output(
            "systemctl list-unit-files --full --all".split(), universal_newlines=True
        ).splitlines():
            if "icecast2.service" in line:
                icecast_exists = True
                break

        if not icecast_exists:
            return HttpResponseBadRequest("Please install icecast2")

        subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_streaming"])
        config_file = os.path.join(settings.BASE_DIR, "setup/mopidy_icecast.conf")
        self._update_mopidy_config(config_file)
        return HttpResponse()

    @option
    def disable_streaming(self, _request: WSGIRequest) -> HttpResponse:
        """Disable icecast streaming."""
        if settings.DOCKER:
            return HttpResponseBadRequest(
                "Choose the correct docker-compose file to control streaming"
            )
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_streaming"])
        config_file = self._get_mopidy_config()
        self._update_mopidy_config(config_file)
        return HttpResponse()

    @option
    def disable_events(self, _request: WSGIRequest) -> None:
        """Disable websocket support."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_events"])

    @option
    def enable_events(self, _request: WSGIRequest) -> None:
        """Enable websocket support."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_events"])

    @option
    def disable_hotspot(self, _request: WSGIRequest) -> None:
        """Disable the wifi created by Raveberry."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_hotspot"])

    @option
    def enable_hotspot(self, _request: WSGIRequest) -> None:
        """Enable the wifi created by Raveberry."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_hotspot"])

    @option
    def unprotect_wifi(self, _request: WSGIRequest) -> None:
        """Disable password protection of the hotspot, making it public."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/unprotect_wifi"])

    @option
    def protect_wifi(self, _request: WSGIRequest) -> None:
        """Enable password protection of the hotspot.
        The password was defined during setup."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/protect_wifi"])

    @option
    def disable_tunneling(self, _request: WSGIRequest) -> None:
        """Disable forwarding of packets to the other network (probably the internet)."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_tunneling"])

    @option
    def enable_tunneling(self, _request: WSGIRequest) -> None:
        """Enable forwarding of packets to the other network.
        Enables clients connected to the hotspot to browse the internet (if available)."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_tunneling"])
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_tunneling"])

    @option
    def disable_remote(self, _request: WSGIRequest) -> None:
        """Disables the connection to an external server."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/disable_remote"])

    @option
    def enable_remote(self, _request: WSGIRequest) -> None:
        """Enables the connection to an external server.
        Allows this instance to be reachable from a public domain."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/enable_remote"])

    @option
    def reboot_server(self, _request: WSGIRequest) -> None:
        """Restarts the server."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/reboot_server"])

    @option
    def reboot_system(self, _request: WSGIRequest) -> None:
        """Reboots the system."""
        subprocess.call(["sudo", "/usr/local/sbin/raveberry/reboot_system"])
