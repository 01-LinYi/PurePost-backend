import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# load environment vars from .env
if os.getenv("IS_PROD", "False") == "True":
    load_dotenv(".env.prod")
else:
    load_dotenv(".env.dev")

BASE_DIR = Path(__file__).resolve().parent.parent

# Secret key for Django project
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY", "on2CD_Ti8EFgXMHFw5Hn2OvuAuo4fE4Nip7DovcSkQBcjtweJvA7-ZL3oX3-Sdb74eg")

# Debug mode
DEBUG = os.getenv("DEBUG", "False") == "True"

# Allowed hosts
#ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost").split(",")
ALLOWED_HOSTS=['127.0.0.1','localhost']

# Installed apps
INSTALLED_APPS = [
    "storages",

    # Django apps
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'django_apscheduler',

    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework.authtoken",
    "corsheaders",

    # Custom apps
    "purepost.auth_service",  # Auth Service app
    "purepost.user_service",  # User Service app
    "purepost.message_service",  # Message Service app
    "purepost.content_moderation",  # Post Service app
    "purepost.social_service",  # Social Service app
    "purepost.deepfake_detection",  # Deepfake Detection app
    "purepost.notification_service",  # Notification Service app
    "purepost.feedback_service",  # Feedback Service app
]

# Middleware
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# CORS configuration
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Root URL configuration
ROOT_URLCONF = "purepost.urls"

# Templates configuration
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# WSGI application
WSGI_APPLICATION = "purepost.wsgi.application"

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / "db.sqlite3",
    }
}

# Uncomment the following to use PostgreSQL in production:
'''
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "purepost"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "password"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}
'''

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

# Authentication and user model
AUTH_USER_MODEL = "auth_service.User"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# REST framework configuration
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "purepost.BaseCursorPagination.BaseCursorPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

# Localization settings
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"

# Celery
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
CELERY_TIMEZONE = TIME_ZONE

# JWT settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# Storage settings. compatible with S3, Django 5
USE_S3 = os.getenv('USE_S3', 'True') == 'True'

if USE_S3:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": os.getenv('AWS_STORAGE_BUCKET_NAME', 'purepost-media'),


                "access_key": os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin'),
                "secret_key": os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin'),


                "endpoint_url": os.getenv('AWS_S3_ENDPOINT_URL', 'http://localhost:9000'),
                "region_name": os.getenv('AWS_S3_REGION_NAME', 'us-east-1'),


                "addressing_style": "path",
                "signature_version": "s3v4",


                "verify": os.getenv('AWS_S3_VERIFY', 'False') == 'True',
                "default_acl": "public-read",


                "querystring_auth": False,


                "file_overwrite": True,
                "max_memory_size": 10 * 1024 * 1024,  # 10MB


                "object_parameters": {
                    "CacheControl": "max-age=86400",
                },
                "custom_domain": None,
            },
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
            "OPTIONS": {

                "bucket_name": os.getenv('AWS_STORAGE_BUCKET_NAME', 'purepost-media'),
                "location": "static",


                "access_key": os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin'),
                "secret_key": os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin'),


                "endpoint_url": os.getenv('AWS_S3_ENDPOINT_URL', 'http://localhost:9000'),
                "region_name": os.getenv('AWS_S3_REGION_NAME', 'us-east-1'),

                "addressing_style": "path",
                "signature_version": "s3v4",


                "verify": os.getenv('AWS_S3_VERIFY', 'False') == 'True',
                "default_acl": "public-read",


                "querystring_auth": False,


                "file_overwrite": True,
            },
        },
    }

    AWS_S3_ENDPOINT_URL = os.getenv(
        'AWS_S3_ENDPOINT_URL', 'http://localhost:9000')
    AWS_STORAGE_BUCKET_NAME = os.getenv(
        'AWS_STORAGE_BUCKET_NAME', 'purepost-media')
    MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"
    STATIC_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/static/"
else:
    # Use local file storage
    MEDIA_ROOT = BASE_DIR / "uploads"
    MEDIA_URL = "/media/"
    STATIC_URL = "/static/"

    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

# Deepfake detection microservice settings
DFDETECT_SERVICE_URL = os.getenv(
    "DFDETECT_SERVICE_URL", "http://localhost:5555")

DFDETECT_SERVICE_TIMEOUT = 30  # Seconds
DEEPFAKE_THRESHOLD = 0.7  # Threshold for alert notifications


# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ASGI_APPLICATION = "purepost.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}

# APScheduler settings
SCHEDULER_CONFIG = {
    "apscheduler.jobstores.default": {
        "class": "django_apscheduler.jobstores:DjangoJobStore"
    },
    "apscheduler.executors.processpool": {
        "type": "threadpool",
        "max_workers": 5
    }
}