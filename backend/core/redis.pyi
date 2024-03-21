from typing import Dict, List, Literal, Tuple, overload

from redis import Redis

DeviceInitialized = Literal[
    "ring_initialized", "wled_initialized", "strip_initialized", "screen_initialized"
]

connection: Redis

def start() -> None: ...

class Event:
    def __init__(self, name: str) -> None: ...
    def wait(self) -> None: ...
    def set(self) -> None: ...
    def clear(self) -> None: ...

@overload
def get(
    key: Literal[
        "playing",
        "paused",
        "playback_error",
        "stop_playback_loop",
        "alarm_playing",
        "alarm_requested",
        "backup_playing",
        "lights_active",
        "ring_initialized",
        "wled_initialized",
        "strip_initialized",
        "screen_initialized",
        "has_internet",
        "mopidy_available",
        "youtube_available",
        "spotify_available",
        "soundcloud_available",
        "jamendo_available",
        "bluetoothctl_active",
    ]
) -> bool: ...
@overload
def get(key: Literal["active_requests"]) -> int: ...
@overload
def get(
    key: Literal["alarm_duration", "last_buzzer", "current_fps", "last_user_count_update"]
) -> float: ...
@overload
def get(key: Literal["active_player", "library_scan_progress"]) -> str: ...
@overload
def get(key: Literal["led_programs", "screen_programs"]) -> List[str]: ...
@overload
def get(key: Literal["resolutions"]) -> List[Tuple[int, int]]: ...
@overload
def get(key: Literal["current_resolution"]) -> Tuple[int, int]: ...
@overload
def get(key: Literal["bluetooth_devices"]) -> List[Dict[str, str]]: ...
@overload
def get(key: Literal["last_requests"]) -> Dict[str, float]: ...
@overload
def put(
    key: Literal[
        "playing",
        "paused",
        "playback_error",
        "stop_playback_loop",
        "alarm_playing",
        "alarm_requested",
        "backup_playing",
        "lights_active",
        "ring_initialized",
        "wled_initialized",
        "strip_initialized",
        "screen_initialized",
        "has_internet",
        "mopidy_available,
        "youtube_available",
        "spotify_available",
        "soundcloud_available",
        "jamendo_available",
        "bluetoothctl_active",
    ],
    value: bool,
) -> None: ...
@overload
def put(key: Literal["active_requests"], value: int) -> None: ...
@overload
def put(
    key: Literal["alarm_duration", "last_buzzer", "current_fps", "last_user_count_update"],
    value: float,
) -> None: ...
@overload
def put(key: Literal["active_player", "library_scan_progress"], value: str) -> None: ...
@overload
def put(key: Literal["led_programs", "screen_programs"], value: List[str]) -> None: ...
@overload
def put(key: Literal["resolutions"], value: List[Tuple[int, int]]) -> None: ...
@overload
def put(key: Literal["current_resolution"], value: Tuple[int, int]) -> None: ...
@overload
def put(key: Literal["bluetooth_devices"], value: List[Dict[str, str]]) -> None: ...
@overload
def put(key: Literal["last_requests"], value: Dict[str, float]) -> None: ...
