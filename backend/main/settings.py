"""This module configures django."""
import logging.config
import os
import pathlib
import subprocess
import sys
from typing import List

import yaml
from django.core.management.utils import get_random_secret_key

from core.util import strtobool

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = strtobool(os.environ.get("DJANGO_DEMO", "0"))

try:
    with open(os.path.join(BASE_DIR, "config/secret_key.txt"), encoding="utf-8") as f:
        SECRET_KEY = f.read().strip()
except FileNotFoundError:
    SECRET_KEY = get_random_secret_key()
    with open(
        os.path.join(BASE_DIR, "config/secret_key.txt"), "w", encoding="utf-8"
    ) as f:
        f.write(SECRET_KEY)
    print("created secret key")

try:
    with open(os.path.join(BASE_DIR, "VERSION"), encoding="utf-8") as f:
        VERSION = f.read().strip()
except FileNotFoundError:
    VERSION = "undefined"

DEBUG = strtobool(os.environ.get("DJANGO_DEBUG", "0"))
TESTING = "test" in sys.argv

DOCKER = strtobool(os.environ.get("DOCKER", "0"))

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    "core.apps.CoreConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
]
if not DEBUG:
    INSTALLED_APPS.append("django.contrib.postgres")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "main.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates/")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

CSRF_FAILURE_VIEW = "core.util.csrf_failure"
with open(os.path.join(BASE_DIR, "config/raveberry.yaml"), encoding="utf-8") as f:
    config = yaml.safe_load(f)
try:
    # Since django 4.0 not only the Referer is checked for csrf protection, but also HTTP_ORIGIN
    # This leads to csrf failures if there is a protocol mismatch
    # e.g. http://demo.raveberry.party vs https://demo.raveberry.party
    # this happens when django is proxied behind a server that does the ssl-handling
    # list the provided remote url as a trusted origin
    remote_url = config["remote_url"]
    # override from environment variable, if present
    env_remote_url = os.environ.get("REMOTE_URL", None)
    if env_remote_url:
        remote_url = env_remote_url
    if remote_url is not None:
        if not remote_url.startswith("https://") and not remote_url.startswith(
            "http://"
        ):
            remote_url = "https://" + remote_url
        CSRF_TRUSTED_ORIGINS = [remote_url]
except KeyError:
    pass

WSGI_APPLICATION = "main.wsgi.application"

# Docker changes
if DOCKER:
    POSTGRES_HOST = "db"
    POSTGRES_PORT = "5432"
    REDIS_HOST = "redis"
    REDIS_PORT = "6379"
    MOPIDY_HOST = "mopidy"
    MOPIDY_PORT = "6680"
    ICECAST_HOST = "icecast"
    ICECAST_PORT = "8000"
    DEFAULT_CACHE_DIR = "/Music/raveberry/"
    TEST_CACHE_DIR = DEFAULT_CACHE_DIR
else:
    POSTGRES_HOST = "127.0.0.1"
    POSTGRES_PORT = "5432"
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = "6379"
    MOPIDY_HOST = "localhost"
    MOPIDY_PORT = "6680"
    ICECAST_HOST = "localhost"
    ICECAST_PORT = "8000"
    DEFAULT_CACHE_DIR = "~/Music/raveberry/"
    TEST_CACHE_DIR = os.path.join(BASE_DIR, "test_cache/")

# Allow these settings to be overwritten with environment variables
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "") or POSTGRES_HOST
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "") or POSTGRES_PORT
REDIS_HOST = os.environ.get("REDIS_HOST", "") or REDIS_HOST
REDIS_PORT = os.environ.get("REDIS_PORT", "") or REDIS_PORT
MOPIDY_HOST = os.environ.get("MOPIDY_HOST", "") or MOPIDY_HOST
MOPIDY_PORT = os.environ.get("MOPIDY_PORT", "") or MOPIDY_PORT
ICECAST_HOST = os.environ.get("ICECAST_HOST", "") or ICECAST_HOST
ICECAST_PORT = os.environ.get("ICECAST_PORT", "") or ICECAST_PORT

# Database
if DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
            "OPTIONS": {"timeout": 20},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "raveberry",
            "USER": "raveberry",
            "PASSWORD": "raveberry",
            "HOST": POSTGRES_HOST,
            "PORT": POSTGRES_PORT,
        }
    }

BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"
CELERY_IMPORTS = [
    "core.lights.worker",
    "core.musiq.playback",
    "core.musiq.music_provider",
    "core.settings.library",
    "core.settings.sound",
]
CELERY_TASK_SERIALIZER = "pickle"
CELERY_ACCEPT_CONTENT = ["pickle"]
if TESTING:
    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# In order to avoid unexpected migrations when the default value is changed to BigAutoField,
# set it here explicitly.
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Users
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "musiq"
LOGOUT_REDIRECT_URL = "musiq"
# only preserve user sessions for an hour
# SESSION_COOKIE_AGE = 3600

# Static files (CSS, JavaScript, Images)
STATIC_FILES = os.path.join(BASE_DIR, "static")
STATICFILES_DIRS: List[str] = [STATIC_FILES]
STATIC_URL = "/static/"

if not os.path.exists(os.path.join(BASE_DIR, "static/admin")):
    import django

    DJANGO_PATH = os.path.dirname(django.__file__)
    STATIC_ADMIN = os.path.join(DJANGO_PATH, "contrib/admin/static/admin")
    if not DOCKER:
        # create symlink to admin static files if not present
        # In the docker setup, the nginx container includes the static files on build
        try:
            os.symlink(
                STATIC_ADMIN,
                os.path.join(BASE_DIR, "static/admin"),
                target_is_directory=True,
            )
            print("linked static admin files")
        except FileExistsError:
            # Sometimes this happened during installation, even though we check right before,
            # maybe because of a race condition.
            # The try/except should prevent crashing the installation.
            pass

# channels
ASGI_APPLICATION = "main.routing.APPLICATION"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [(REDIS_HOST, REDIS_PORT)], "capacity": 1500, "expiry": 10},
    }
}

# Logging

# avoid creating a logger in every module
# https://stackoverflow.com/questions/34726515/avoid-logger-logging-getlogger-name
logging.basicConfig()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "precise": {
            "format": "%(asctime)s %(module)s.%(funcName)s:%(lineno)s %(levelname)s  %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "brief": {
            "format": "%(module)s.%(funcName)s:%(lineno)s %(levelname)s  %(message)s"
        },
    },
    "handlers": {
        "infofile": {
            "level": "INFO",
            "formatter": "precise",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/info.log"),
            "maxBytes": 1024 * 1024 * 15,  # 15MB
            "backupCount": 10,
        },
        "errorfile": {
            "level": "ERROR",
            "formatter": "precise",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/error.log"),
            "maxBytes": 1024 * 1024 * 15,  # 15MB
            "backupCount": 10,
        },
        "console": {
            "level": "INFO",
            "formatter": "brief",
            "class": "logging.StreamHandler",
        },
        "docker": {
            "level": "INFO",
            "formatter": "precise",
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["infofile", "errorfile", "console"]
        if DEBUG or TESTING
        else ["infofile", "errorfile", "docker"]
        if DOCKER
        else ["infofile", "errorfile"],
        "level": "DEBUG",
    },
}
LOGGING_CONFIG = None  # disables Django handling of logging
logging.config.dictConfig(LOGGING)

# In local networks Raveberry is only accessible via http, secure cookies are not possible there.
# If Raveberry is only used with https, these should be enabled.
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

# app settings
try:
    with open(os.path.join(BASE_DIR, "config/cache_dir"), encoding="utf-8") as f:
        SONGS_CACHE_DIR = f.read().strip()
except FileNotFoundError:
    SONGS_CACHE_DIR = ""
if SONGS_CACHE_DIR == "":
    SONGS_CACHE_DIR = os.path.expanduser(DEFAULT_CACHE_DIR)
    with open(os.path.join(BASE_DIR, "config/cache_dir"), "w", encoding="utf-8") as f:
        f.write(SONGS_CACHE_DIR)
    print(f"no song caching directory specified, using {DEFAULT_CACHE_DIR}")

# sound
PULSE_SERVER = "127.0.0.1"
if DEBUG:
    try:
        output = subprocess.check_output(
            "pactl info".split(), text=True, stderr=subprocess.DEVNULL
        )
        PULSE_SERVER = output.splitlines()[0].split(":")[1].strip()
    except (FileNotFoundError, subprocess.CalledProcessError, IndexError):
        pass

# use a different cache directory for testing
if TESTING:
    SONGS_CACHE_DIR = TEST_CACHE_DIR

pathlib.Path(SONGS_CACHE_DIR).mkdir(parents=True, exist_ok=True)
