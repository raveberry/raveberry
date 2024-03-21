"""This module provides functionality to interface with Redis."""
from ast import literal_eval
from typing import Any, Dict, List, Optional, Tuple, Union, Literal

from django.conf import settings as conf
from redis import Redis

from core.util import strtobool

# locks:
# mopidy_lock:  controlling mopidy api accesses
# lights_lock:  ensures lights settings are not changed during device updates

# channels
# lights_settings_changed

DeviceInitialized = Literal

# values:
# maps key to default and type of value
defaults = {
    # playback
    "active_player": "fake",
    "playing": False,
    "paused": False,
    "playback_error": False,
    "stop_playback_loop": False,
    "alarm_playing": False,
    "alarm_requested": False,
    "alarm_duration": 10.0,
    "last_buzzer": 0.0,
    "backup_playing": False,
    # lights
    "lights_active": False,
    "ring_initialized": False,
    "wled_initialized": False,
    "strip_initialized": False,
    "screen_initialized": False,
    "led_programs": [],
    "screen_programs": [],
    "resolutions": [],
    "current_resolution": (0, 0),
    "current_fps": 0.0,
    # settings
    "has_internet": False,
    "mopidy_available": False,
    "youtube_available": False,
    "spotify_available": False,
    "soundcloud_available": False,
    "jamendo_available": False,
    "library_scan_progress": "0 / 0 / 0",
    "bluetoothctl_active": False,
    "bluetooth_devices": [],
    # user manager
    "active_requests": 0,
    "last_user_count_update": 0.0,
    "last_requests": {},
}

connection = Redis(host=conf.REDIS_HOST, port=conf.REDIS_PORT, decode_responses=True)


def start() -> None:
    """Initializes the module by clearing all keys."""
    connection.flushdb()


def get(key: str) -> Union[bool, int, float, str, List, Dict, Tuple]:
    """This method returns the value for the given :param key: from redis.
    Vaules of non-existing keys are set to their respective default value."""
    # values are stored as string in redis
    # cast the value to its respective type, defined by the default value, before returning it
    default = defaults[key]
    value = connection.get(key)
    if value is None:
        return default
    if type(default) is bool:
        return strtobool(value)
    if type(default) in (list, dict, tuple):
        # evaluate the stored literal
        return literal_eval(value)
    return type(default)(value)


def put(key: str, value: Any, expire: Optional[float] = None) -> None:
    """This method sets the value for the given :param key: to the given :param value:.
    If set, the key will expire after :param ex: seconds."""
    connection.set(key, str(value), ex=expire)


class Event:
    """A class that provides basic functionality similar to threading.Event using redis."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.is_set = False
        self.lock = connection.lock(f"{self.name}_lock")

    def wait(self) -> None:
        """Blocks until the event is set."""
        with self.lock:
            is_set = self.is_set
        if is_set:
            return
        pubsub = connection.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(self.name)
        next(pubsub.listen())
        pubsub.close()

    def set(self) -> None:
        """Set the event and wake up all waiting threads."""
        with self.lock:
            self.is_set = True
            connection.publish(self.name, "")

    def clear(self) -> None:
        """Clear this Event, allowing threads to wait for it."""
        with self.lock:
            self.is_set = False
