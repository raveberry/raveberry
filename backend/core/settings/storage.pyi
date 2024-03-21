from typing import Literal, overload

from cachetools import TTLCache

# Sometimes the storage functions are accessed dynamically.
# Comfort mypy by telling it the value will still be one of the specified ones.

class Interactivity:
        full_control = "Full Public Control"
        full_voting = "Up- and Downvoting"
        upvotes_only = "Upvotes Only"
        no_control = "No Control"

class Privileges:
        everybody = "Everybody"
        mod = "Mod and Admin"
        admin = "Admin Only"
        nobody = "Nobody"

PlatformEnabled = Literal[
    "local_enabled",
    "youtube_enabled",
    "spotify_enabled",
    "soundcloud_enabled",
    "jamendo_enabled",
]

PlatformSuggestions = Literal[
    "youtube_suggestions",
    "spotify_suggestions",
    "soundcloud_suggestions",
    "jamendo_suggestions",
]

DeviceBrightness = Literal[
    "ring_brightness", "strip_brightness", "wled_brightness", "screen_brightness"
]
DeviceMonochrome = Literal[
    "ring_monochrome", "strip_monochrome", "wled_monochrome", "screen_monochrome"
]
DeviceProgram = Literal[
    "ring_program",
    "last_ring_program",
    "strip_program",
    "last_strip_program",
    "wled_program",
    "last_wled_program",
    "screen_program",
    "last_screen_program",
]

cache: TTLCache = TTLCache(ttl=10, maxsize=128)

@overload
def get(
    key: Literal[
        "ip_checking",
        "logging_enabled",
        "hashtags_active",
        "privileged_stream",
        "online_suggestions",
        "new_music_only",
        "enqueue_first",
        "local_enabled",
        "youtube_enabled",
        "spotify_enabled",
        "soundcloud_enabled",
        "jamendo_enabled",
        "feed_cava",
        "paused",
        "shuffle",
        "repeat",
        "autoplay",
        "ring_monochrome",
        "strip_monochrome",
        "wled_monochrome",
        "screen_monochrome",
        "dynamic_resolution",
    ]
) -> bool: ...
@overload
def get(
    key: Literal[
        "next_color_index",
        "downvotes_to_kick",
        "number_of_suggestions",
        "max_playlist_items",
        "max_queue_length",
        "people_to_party",
        "youtube_suggestions",
        "spotify_suggestions",
        "jamendo_suggestions",
        "soundcloud_suggestions",
        "wled_led_count",
        "wled_port",
    ]
) -> int: ...
@overload
def get(
    key: Literal[
        "color_offset",
        "song_cooldown",
        "max_download_size",
        "alarm_probability",
        "buzzer_cooldown",
        "buzzer_success_probability",
        "volume",
        "ups",
        "program_speed",
        "ring_brightness",
        "strip_brightness",
        "wled_brightness",
        "screen_brightness",
    ]
) -> float: ...
@overload
def get(
    key: Literal[
        "interactivity",
        "color_indication",
        "connectivity_host",
        "additional_keywords",
        "forbidden_keywords",
        "spotify_username",
        "spotify_password",
        "spotify_device_client_id",
        "spotify_device_client_secret",
        "spotify_mopidy_client_id",
        "spotify_mopidy_client_secret",
        "spotify_redirect_uri",
        "spotify_authorized_url",
        "spotipy_token_info",
        "soundcloud_auth_token",
        "jamendo_client_id",
        "output",
        "backup_stream",
        "wled_ip",
        "ring_program",
        "last_ring_program",
        "strip_program",
        "last_strip_program",
        "wled_program",
        "last_wled_program",
        "screen_program",
        "last_screen_program",
    ]
) -> str: ...
@overload
def get(key: Literal["initial_resolution"]) -> tuple[int, int]: ...
@overload
def get(key: Literal["fixed_color"]) -> tuple[float, float, float]: ...
@overload
def put(
    key: Literal[
        "ip_checking",
        "logging_enabled",
        "hashtags_active",
        "privileged_stream",
        "online_suggestions",
        "new_music_only",
        "enqueue_first",
        "local_enabled",
        "youtube_enabled",
        "spotify_enabled",
        "soundcloud_enabled",
        "jamendo_enabled",
        "feed_cava",
        "paused",
        "shuffle",
        "repeat",
        "autoplay",
        "ring_monochrome",
        "strip_monochrome",
        "wled_monochrome",
        "screen_monochrome",
        "dynamic_resolution",
    ],
    value: bool,
) -> None: ...
@overload
def put(
    key: Literal[
        "next_color_index",
        "downvotes_to_kick",
        "number_of_suggestions",
        "max_playlist_items",
        "max_queue_length",
        "people_to_party",
        "youtube_suggestions",
        "spotify_suggestions",
        "jamendo_suggestions",
        "soundcloud_suggestions",
        "wled_led_count",
        "wled_port",
    ],
    value: int,
) -> None: ...
@overload
def put(
    key: Literal[
        "color_offset",
        "song_cooldown",
        "max_download_size",
        "alarm_probability",
        "buzzer_cooldown",
        "buzzer_success_probability",
        "volume",
        "ups",
        "program_speed",
        "ring_brightness",
        "strip_brightness",
        "wled_brightness",
        "screen_brightness",
    ],
    value: float,
) -> None: ...
@overload
def put(
    key: Literal[
        "interactivity",
        "color_indication",
        "connectivity_host",
        "additional_keywords",
        "forbidden_keywords",
        "spotify_username",
        "spotify_password",
        "spotify_device_client_id",
        "spotify_device_client_secret",
        "spotify_mopidy_client_id",
        "spotify_mopidy_client_secret",
        "spotify_redirect_uri",
        "spotify_authorized_url",
        "spotipy_token_info",
        "soundcloud_auth_token",
        "jamendo_client_id",
        "output",
        "backup_stream",
        "wled_ip",
        "ring_program",
        "last_ring_program",
        "strip_program",
        "last_strip_program",
        "wled_program",
        "last_wled_program",
        "screen_program",
        "last_screen_program",
    ],
    value: str,
) -> None: ...
@overload
def put(key: Literal["initial_resolution"], value: tuple[int, int]) -> None: ...
@overload
def put(key: Literal["fixed_color"], value: tuple[float, float, float]) -> None: ...
