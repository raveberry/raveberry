"""This module contains all url endpoints and maps them to their corresponding functions."""

import re

from django.urls import include, URLPattern
from django.urls import path
from django.views.generic import RedirectView

from core import mock
from main import settings

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
    path("suggestions/", BASE.musiq.suggestions.get_suggestions, name="suggestions"),
    path("restart/", BASE.musiq.controller.restart, name="restart_song"),
    path("seek_backward/", BASE.musiq.controller.seek_backward, name="seek_backward"),
    path("play/", BASE.musiq.controller.play, name="play_song"),
    path("pause/", BASE.musiq.controller.pause, name="pause_song"),
    path("seek_forward/", BASE.musiq.controller.seek_forward, name="seek_forward"),
    path("skip/", BASE.musiq.controller.skip, name="skip_song"),
    path("set_shuffle/", BASE.musiq.controller.set_shuffle, name="set_shuffle"),
    path("set_repeat/", BASE.musiq.controller.set_repeat, name="set_repeat"),
    path("set_autoplay/", BASE.musiq.controller.set_autoplay, name="set_autoplay"),
    path("request_radio/", BASE.musiq.request_radio, name="request_radio"),
    path("set_volume/", BASE.musiq.controller.set_volume, name="set_volume"),
    path("remove_all/", BASE.musiq.controller.remove_all, name="remove_all"),
    path("prioritize/", BASE.musiq.controller.prioritize, name="prioritize_song"),
    path("remove/", BASE.musiq.controller.remove, name="remove_song"),
    path("reorder/", BASE.musiq.controller.reorder, name="reorder_song"),
    path("vote_up/", BASE.musiq.controller.vote_up, name="vote_up_song"),
    path("vote_down/", BASE.musiq.controller.vote_down, name="vote_down_song"),
]

LIGHTS_URLS = [
    path("state/", BASE.lights.get_state, name="lights_state"),
    path(
        "shortcut/",
        BASE.lights.controller.set_lights_shortcut,
        name="set_lights_shortcut",
    ),
    path(
        "set_ring_program/",
        BASE.lights.controller.set_ring_program,
        name="set_ring_program",
    ),
    path(
        "set_ring_brightness/",
        BASE.lights.controller.set_ring_brightness,
        name="set_ring_brightness",
    ),
    path(
        "set_ring_monochrome/",
        BASE.lights.controller.set_ring_monochrome,
        name="set_ring_monochrome",
    ),
    path(
        "set_wled_led_count/",
        BASE.lights.controller.set_wled_led_count,
        name="set_wled_led_count",
    ),
    path("set_wled_ip/", BASE.lights.controller.set_wled_ip, name="set_wled_ip",),
    path("set_wled_port/", BASE.lights.controller.set_wled_port, name="set_wled_port",),
    path(
        "set_wled_program/",
        BASE.lights.controller.set_wled_program,
        name="set_wled_program",
    ),
    path(
        "set_wled_brightness/",
        BASE.lights.controller.set_wled_brightness,
        name="set_wled_brightness",
    ),
    path(
        "set_wled_monochrome/",
        BASE.lights.controller.set_wled_monochrome,
        name="set_wled_monochrome",
    ),
    path(
        "set_strip_program/",
        BASE.lights.controller.set_strip_program,
        name="set_strip_program",
    ),
    path(
        "set_strip_brightness/",
        BASE.lights.controller.set_strip_brightness,
        name="set_strip_brightness",
    ),
    path("adjust_screen/", BASE.lights.controller.adjust_screen, name="adjust_screen"),
    path(
        "set_screen_program/",
        BASE.lights.controller.set_screen_program,
        name="set_screen_program",
    ),
    path(
        "set_program_speed/",
        BASE.lights.controller.set_program_speed,
        name="set_program_speed",
    ),
    path(
        "set_fixed_color/",
        BASE.lights.controller.set_fixed_color,
        name="set_fixed_color",
    ),
]

SETTINGS_URLS = [
    path("state/", BASE.settings.get_state, name="settings_state"),
    path(
        "set_voting_system/",
        BASE.settings.basic.set_voting_system,
        name="set_voting_system",
    ),
    path(
        "set_new_music_only/",
        BASE.settings.basic.set_new_music_only,
        name="set_new_music_only",
    ),
    path(
        "set_logging_enabled/",
        BASE.settings.basic.set_logging_enabled,
        name="set_logging_enabled",
    ),
    path(
        "set_online_suggestions/",
        BASE.settings.basic.set_online_suggestions,
        name="set_online_suggestions",
    ),
    path(
        "set_number_of_suggestions/",
        BASE.settings.basic.set_number_of_suggestions,
        name="set_number_of_suggestions",
    ),
    path(
        "set_people_to_party/",
        BASE.settings.basic.set_people_to_party,
        name="set_people_to_party",
    ),
    path(
        "set_alarm_probability/",
        BASE.settings.basic.set_alarm_probability,
        name="set_alarm_probability",
    ),
    path(
        "set_downvotes_to_kick/",
        BASE.settings.basic.set_downvotes_to_kick,
        name="set_downvotes_to_kick",
    ),
    path(
        "set_additional_keywords/",
        BASE.settings.basic.set_additional_keywords,
        name="set_additional_keywords",
    ),
    path(
        "set_forbidden_keywords/",
        BASE.settings.basic.set_forbidden_keywords,
        name="set_forbidden_keywords",
    ),
    path(
        "set_max_download_size/",
        BASE.settings.basic.set_max_download_size,
        name="set_max_download_size",
    ),
    path(
        "set_max_playlist_items/",
        BASE.settings.basic.set_max_playlist_items,
        name="set_max_playlist_items",
    ),
    path("check_internet/", BASE.settings.basic.check_internet, name="check_internet"),
    path(
        "update_user_count/",
        BASE.settings.basic.update_user_count,
        name="update_user_count",
    ),
    path(
        "set_youtube_enabled/",
        BASE.settings.platforms.set_youtube_enabled,
        name="set_youtube_enabled",
    ),
    path(
        "set_youtube_suggestions/",
        BASE.settings.platforms.set_youtube_suggestions,
        name="set_youtube_suggestions",
    ),
    path(
        "set_spotify_enabled/",
        BASE.settings.platforms.set_spotify_enabled,
        name="set_spotify_enabled",
    ),
    path(
        "set_spotify_suggestions/",
        BASE.settings.platforms.set_spotify_suggestions,
        name="set_spotify_suggestions",
    ),
    path(
        "set_spotify_credentials/",
        BASE.settings.platforms.set_spotify_credentials,
        name="set_spotify_credentials",
    ),
    path(
        "set_soundcloud_enabled/",
        BASE.settings.platforms.set_soundcloud_enabled,
        name="set_soundcloud_enabled",
    ),
    path(
        "set_soundcloud_suggestions/",
        BASE.settings.platforms.set_soundcloud_suggestions,
        name="set_soundcloud_suggestions",
    ),
    path(
        "set_soundcloud_credentials/",
        BASE.settings.platforms.set_soundcloud_credentials,
        name="set_soundcloud_credentials",
    ),
    path(
        "set_bluetooth_scanning/",
        BASE.settings.sound.set_bluetooth_scanning,
        name="set_bluetooth_scanning",
    ),
    path(
        "connect_bluetooth/",
        BASE.settings.sound.connect_bluetooth,
        name="connect_bluetooth",
    ),
    path(
        "disconnect_bluetooth/",
        BASE.settings.sound.disconnect_bluetooth,
        name="disconnect_bluetooth",
    ),
    path("output_devices/", BASE.settings.sound.output_devices, name="output_devices",),
    path(
        "set_output_device/",
        BASE.settings.sound.set_output_device,
        name="set_output_device",
    ),
    path(
        "available_ssids/", BASE.settings.wifi.available_ssids, name="available_ssids",
    ),
    path(
        "connect_to_wifi/", BASE.settings.wifi.connect_to_wifi, name="connect_to_wifi",
    ),
    path(
        "enable_homewifi/", BASE.settings.wifi.enable_homewifi, name="enable_homewifi",
    ),
    path(
        "disable_homewifi/",
        BASE.settings.wifi.disable_homewifi,
        name="disable_homewifi",
    ),
    path("stored_ssids/", BASE.settings.wifi.stored_ssids, name="stored_ssids"),
    path(
        "set_homewifi_ssid/",
        BASE.settings.wifi.set_homewifi_ssid,
        name="set_homewifi_ssid",
    ),
    path(
        "list_subdirectories/",
        BASE.settings.library.list_subdirectories,
        name="list_subdirectories",
    ),
    path("scan_library/", BASE.settings.library.scan_library, name="scan_library"),
    path(
        "create_playlists/",
        BASE.settings.library.create_playlists,
        name="create_playlists",
    ),
    path("analyse/", BASE.settings.analysis.analyse, name="analyse"),
    path(
        "disable_streaming/",
        BASE.settings.system.disable_streaming,
        name="disable_streaming",
    ),
    path(
        "enable_streaming/",
        BASE.settings.system.enable_streaming,
        name="enable_streaming",
    ),
    path(
        "disable_events/", BASE.settings.system.disable_events, name="disable_events",
    ),
    path("enable_events/", BASE.settings.system.enable_events, name="enable_events"),
    path(
        "disable_hotspot/",
        BASE.settings.system.disable_hotspot,
        name="disable_hotspot",
    ),
    path(
        "enable_hotspot/", BASE.settings.system.enable_hotspot, name="enable_hotspot",
    ),
    path(
        "unprotect_wifi/", BASE.settings.system.unprotect_wifi, name="unprotect_wifi",
    ),
    path("protect_wifi/", BASE.settings.system.protect_wifi, name="protect_wifi"),
    path(
        "disable_tunneling/",
        BASE.settings.system.disable_tunneling,
        name="disable_tunneling",
    ),
    path(
        "enable_tunneling/",
        BASE.settings.system.enable_tunneling,
        name="enable_tunneling",
    ),
    path(
        "disable_remote/", BASE.settings.system.disable_remote, name="disable_remote",
    ),
    path("enable_remote/", BASE.settings.system.enable_remote, name="enable_remote"),
    path("reboot_server/", BASE.settings.system.reboot_server, name="reboot_server"),
    path("reboot_system/", BASE.settings.system.reboot_system, name="reboot_system"),
    path(
        "shutdown_system/", BASE.settings.system.shutdown_system, name="shutdown_system"
    ),
    path(
        "get_latest_version/",
        BASE.settings.system.get_latest_version,
        name="get_latest_version",
    ),
    path(
        "get_upgrade_config/",
        BASE.settings.system.get_upgrade_config,
        name="get_upgrade_config",
    ),
    path(
        "upgrade_raveberry/",
        BASE.settings.system.upgrade_raveberry,
        name="upgrade_raveberry",
    ),
]

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="musiq", permanent=False), name="base"),
    path("musiq/", BASE.musiq.index, name="musiq"),
    path("lights/", BASE.lights.index, name="lights"),
    path("stream/", BASE.no_stream, name="no_stream"),
    path("network_info/", BASE.network_info.index, name="network_info"),
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
                        [path("post_song/", BASE.musiq.post_song, name="post_song"),]
                    ),
                ),
            ]
        ),
    ),
]

if settings.MOCK:
    for url in urlpatterns:
        if isinstance(url, URLPattern):
            url.callback = mock.index
else:
    BASE.start()
