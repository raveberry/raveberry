import os
import sys
import pathlib

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    with open(os.path.join(BASE_DIR, 'config/secret_key.txt')) as f:
        SECRET_KEY = f.read().strip()
except FileNotFoundError:
    from django.core.management.utils import get_random_secret_key
    SECRET_KEY = get_random_secret_key()
    with open(os.path.join(BASE_DIR, 'config/secret_key.txt'), 'w') as f:
        f.write(SECRET_KEY)
    print('created secret key')

if os.environ.get('DJANGO_DEBUG'):
    DEBUG = True
else:
    DEBUG = False

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'core.apps.CoreConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'compressor',
    'sass_processor',
    'channels',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.user_manager.SimpleMiddleware',
]

ROOT_URLCONF = 'main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates/'),
            ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'main.wsgi.application'


# Database

if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
            'OPTIONS': {
                'timeout': 20,
            }
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'raveberry',
            'USER': 'raveberry',
            'PASSWORD': 'raveberry',
            'HOST': '127.0.0.1',
            'PORT': '5432',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Berlin'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Users
LOGIN_REDIRECT_URL = '/logged_in/'
LOGOUT_REDIRECT_URL = '/'
# only preserve user sessions for an hour
#SESSION_COOKIE_AGE = 3600

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [
        #os.path.join(BASE_DIR, "staticfiles/"),
        ]
STATIC_URL = '/static/'

# create symlink to admin static files if not present
if not os.path.islink(os.path.join(BASE_DIR, 'static/admin')):
    import django
    django_path = os.path.dirname(django.__file__)
    static_admin = os.path.join(django_path, 'contrib/admin/static/admin')
    os.symlink(static_admin, os.path.join(BASE_DIR, 'static/admin'), target_is_directory=True)
    print('linked static admin files')


# adapted for django-compressor and sass-processor
SASS_PROCESSOR_ROOT = STATIC_ROOT

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # other finders..
    'compressor.finders.CompressorFinder',
    'sass_processor.finders.CssFinder',
)

# channels
ASGI_APPLICATION = "main.routing.application"
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'infofile': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/info.log'),
            'maxBytes': 1024*1024*15, # 15MB
            'backupCount': 10,
        },
        'errorfile': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/error.log'),
            'maxBytes': 1024*1024*15, # 15MB
            'backupCount': 10,
        },
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'raveberry': {
            'handlers': ['infofile', 'errorfile'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['errorfile'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

# Security Settings
#SECURE_CONTENT_TYPE_NOSNIFF = True
#SECURE_BROWSER_XSS_FILTER = True
#SESSION_COOKIE_SECURE = True
#CSRF_COOKIE_SECURE = True
#X_FRAME_OPTIONS = 'DENY'

# app settings
try:
    with open(os.path.join(BASE_DIR, 'config/cache_dir')) as f:
        SONGS_CACHE_DIR = f.read().strip()
except FileNotFoundError:
    SONGS_CACHE_DIR = ''
if SONGS_CACHE_DIR == '':
    SONGS_CACHE_DIR = os.path.expanduser('~/Music/raveberry/')
    with open(os.path.join(BASE_DIR, 'config/cache_dir'), 'w') as f:
        f.write(SONGS_CACHE_DIR)
    print('no song caching directory specified, using ~/Music/raveberry/')

# use a different cache directory for testing
if 'test' in sys.argv:
    SONGS_CACHE_DIR = os.path.join(BASE_DIR, 'test_cache/')

pathlib.Path(SONGS_CACHE_DIR).mkdir(parents=True, exist_ok=True)
