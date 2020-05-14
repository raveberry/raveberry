"""This module contains all url endpoints and maps them to their corresponding functions."""

import os
import re

from django.urls import include
from django.urls import path
from django.views.generic import RedirectView

if os.environ.get("DJANGO_MOCK"):
    import core.mock

    # Mock all url names so they can be reversed.
    url_names = []
    with open(__file__) as urls:
        for line in urls:
            match = re.search(r'name="(\w+)"', line)
            if match:
                url_names.append(match.groups()[0])
    urlpatterns = [path("", core.mock.index, name=url_name) for url_name in url_names]
else:
    from core.base import Base

    BASE = Base()

    MUSIQ_URLS = [
        path("state/", BASE.musiq.get_state, name="musiq_state"),
        path(
            "random_suggestion/",
            BASE.musiq.suggestions.random_suggestion,
            name="random_suggestion",
        ),
        path("request_music/", BASE.musiq.request_music, name="request_music"),
        path(
            "suggestions/", BASE.musiq.suggestions.get_suggestions, name="suggestions"
        ),
        path("restart/", BASE.musiq.player.restart, name="restart_song"),
        path("seek_backward/", BASE.musiq.player.seek_backward, name="seek_backward"),
        path("play/", BASE.musiq.player.play, name="play_song"),
        path("pause/", BASE.musiq.player.pause, name="pause_song"),
        path("seek_forward/", BASE.musiq.player.seek_forward, name="seek_forward"),
        path("skip/", BASE.musiq.player.skip, name="skip_song"),
        path("set_shuffle/", BASE.musiq.player.set_shuffle, name="set_shuffle"),
        path("set_repeat/", BASE.musiq.player.set_repeat, name="set_repeat"),
        path("set_autoplay/", BASE.musiq.player.set_autoplay, name="set_autoplay"),
        path("request_radio/", BASE.musiq.request_radio, name="request_radio"),
        path("set_volume/", BASE.musiq.player.set_volume, name="set_volume"),
        path("remove_all/", BASE.musiq.player.remove_all, name="remove_all"),
        path("prioritize/", BASE.musiq.player.prioritize, name="prioritize_song"),
        path("remove/", BASE.musiq.player.remove, name="remove_song"),
        path("reorder/", BASE.musiq.player.reorder, name="reorder_song"),
        path("vote_up/", BASE.musiq.player.vote_up, name="vote_up_song"),
        path("vote_down/", BASE.musiq.player.vote_down, name="vote_down_song"),
    ]

    LIGHTS_URLS = [
        path("state/", BASE.lights.get_state, name="lights_state"),
        path("shortcut/", BASE.lights.set_lights_shortcut, name="set_lights_shortcut"),
        path(
            "set_ring_program/", BASE.lights.set_ring_program, name="set_ring_program"
        ),
        path(
            "set_ring_brightness/",
            BASE.lights.set_ring_brightness,
            name="set_ring_brightness",
        ),
        path(
            "set_ring_monochrome/",
            BASE.lights.set_ring_monochrome,
            name="set_ring_monochrome",
        ),
        path(
            "set_strip_program/",
            BASE.lights.set_strip_program,
            name="set_strip_program",
        ),
        path(
            "set_strip_brightness/",
            BASE.lights.set_strip_brightness,
            name="set_strip_brightness",
        ),
        path("adjust_screen/", BASE.lights.adjust_screen, name="adjust_screen"),
        path(
            "set_screen_program/",
            BASE.lights.set_screen_program,
            name="set_screen_program",
        ),
        path(
            "set_program_speed/",
            BASE.lights.set_program_speed,
            name="set_program_speed",
        ),
        path("set_fixed_color/", BASE.lights.set_fixed_color, name="set_fixed_color"),
    ]

    PAD_URLS = [
        path("state/", BASE.pad.get_state, name="pad_state"),
        path("submit/", BASE.pad.submit, name="submit_pad"),
    ]

    SETTINGS_URLS = [
        path("state/", BASE.settings.get_state, name="settings_state"),
        path(
            "set_voting_system/",
            BASE.settings.set_voting_system,
            name="set_voting_system",
        ),
        path(
            "set_logging_enabled/",
            BASE.settings.set_logging_enabled,
            name="set_logging_enabled",
        ),
        path(
            "set_people_to_party/",
            BASE.settings.set_people_to_party,
            name="set_people_to_party",
        ),
        path(
            "set_alarm_probability/",
            BASE.settings.set_alarm_probability,
            name="set_alarm_probability",
        ),
        path(
            "set_downvotes_to_kick/",
            BASE.settings.set_downvotes_to_kick,
            name="set_downvotes_to_kick",
        ),
        path(
            "set_max_download_size/",
            BASE.settings.set_max_download_size,
            name="set_max_download_size",
        ),
        path(
            "set_max_playlist_items/",
            BASE.settings.set_max_playlist_items,
            name="set_max_playlist_items",
        ),
        path("check_internet/", BASE.settings.check_internet, name="check_internet"),
        path(
            "update_user_count/",
            BASE.settings.update_user_count,
            name="update_user_count",
        ),
        path(
            "set_youtube_enabled/",
            BASE.settings.set_youtube_enabled,
            name="set_youtube_enabled",
        ),
        path(
            "check_spotify_credentials/",
            BASE.settings.check_spotify_credentials,
            name="check_spotify_credentials",
        ),
        path(
            "set_spotify_credentials/",
            BASE.settings.set_spotify_credentials,
            name="set_spotify_credentials",
        ),
        path(
            "set_bluetooth_scanning/",
            BASE.settings.set_bluetooth_scanning,
            name="set_bluetooth_scanning",
        ),
        path(
            "connect_bluetooth/",
            BASE.settings.connect_bluetooth,
            name="connect_bluetooth",
        ),
        path(
            "disconnect_bluetooth/",
            BASE.settings.disconnect_bluetooth,
            name="disconnect_bluetooth",
        ),
        path("output_devices/", BASE.settings.output_devices, name="output_devices",),
        path(
            "set_output_device/",
            BASE.settings.set_output_device,
            name="set_output_device",
        ),
        path("available_ssids/", BASE.settings.available_ssids, name="available_ssids"),
        path("connect_to_wifi/", BASE.settings.connect_to_wifi, name="connect_to_wifi"),
        path("enable_homewifi/", BASE.settings.enable_homewifi, name="enable_homewifi"),
        path(
            "disable_homewifi/", BASE.settings.disable_homewifi, name="disable_homewifi"
        ),
        path("stored_ssids/", BASE.settings.stored_ssids, name="stored_ssids"),
        path(
            "set_homewifi_ssid/",
            BASE.settings.set_homewifi_ssid,
            name="set_homewifi_ssid",
        ),
        path(
            "list_subdirectories/",
            BASE.settings.list_subdirectories,
            name="list_subdirectories",
        ),
        path("scan_library/", BASE.settings.scan_library, name="scan_library"),
        path(
            "create_playlists/", BASE.settings.create_playlists, name="create_playlists"
        ),
        path("analyse/", BASE.settings.analyse, name="analyse"),
        path(
            "disable_streaming/",
            BASE.settings.disable_streaming,
            name="disable_streaming",
        ),
        path(
            "enable_streaming/", BASE.settings.enable_streaming, name="enable_streaming"
        ),
        path("disable_events/", BASE.settings.disable_events, name="disable_events"),
        path("enable_events/", BASE.settings.enable_events, name="enable_events"),
        path("disable_hotspot/", BASE.settings.disable_hotspot, name="disable_hotspot"),
        path("enable_hotspot/", BASE.settings.enable_hotspot, name="enable_hotspot"),
        path("unprotect_wifi/", BASE.settings.unprotect_wifi, name="unprotect_wifi"),
        path("protect_wifi/", BASE.settings.protect_wifi, name="protect_wifi"),
        path(
            "disable_tunneling/",
            BASE.settings.disable_tunneling,
            name="disable_tunneling",
        ),
        path(
            "enable_tunneling/", BASE.settings.enable_tunneling, name="enable_tunneling"
        ),
        path("disable_remote/", BASE.settings.disable_remote, name="disable_remote"),
        path("enable_remote/", BASE.settings.enable_remote, name="enable_remote"),
        path("reboot_server/", BASE.settings.reboot_server, name="reboot_server"),
        path("reboot_system/", BASE.settings.reboot_system, name="reboot_system"),
    ]

    urlpatterns = [
        path(
            "", RedirectView.as_view(pattern_name="musiq", permanent=False), name="base"
        ),
        path("musiq/", BASE.musiq.index, name="musiq"),
        path("lights/", BASE.lights.index, name="lights"),
        path("pad/", BASE.pad.index, name="pad"),
        path("stream/", BASE.no_stream, name="no_stream"),
        path("settings/", BASE.settings.index, name="settings"),
        path("accounts/", include("django.contrib.auth.urls")),
        path("login/", RedirectView.as_view(pattern_name="login", permanent=False)),
        path("logged_in/", BASE.logged_in, name="logged_in"),
        path("logout/", RedirectView.as_view(pattern_name="logout", permanent=False)),
        path(
            "ajax/",
            include(
                [
                    path("state/", BASE.get_state, name="base_state"),
                    path("submit_hashtag/", BASE.submit_hashtag, name="submit_hashtag"),
                    path("musiq/", include(MUSIQ_URLS)),
                    path("lights/", include(LIGHTS_URLS)),
                    path("pad/", include(PAD_URLS)),
                    path("settings/", include(SETTINGS_URLS)),
                ]
            ),
        ),
        path(
            "api/",
            include(
                [
                    path(
                        "musiq/",
                        include(
                            [
                                path(
                                    "post_song/", BASE.musiq.post_song, name="post_song"
                                ),
                            ]
                        ),
                    ),
                ]
            ),
        ),
    ]
