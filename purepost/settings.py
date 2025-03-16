import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# Secret key for Django project
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY", "on2CD_Ti8EFgXMHFw5Hn2OvuAuo4fE4Nip7DovcSkQBcjtweJvA7-ZL3oX3-Sdb74eg")

# Debug mode
DEBUG = os.getenv("DEBUG", "False") == "True"

# Allowed hosts
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost").split(",")

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

    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework.authtoken",
    "corsheaders",

    # Custom apps
    "purepost.auth_service",  # Authentication service
    "purepost.user_service",  # User service
    "purepost.message_service",  # Message service
    "purepost.content_moderation",  # Content moderation (Post) service
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
        "DIRS": [],
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
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

# JWT settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# Localization settings
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True


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

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ASGI_APPLICATION = "purepost.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(os.getenv("REDIS_HOST", "localhost"), int(os.getenv("REDIS_PORT", 6379)))],
        },
    },
}
