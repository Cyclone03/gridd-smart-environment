"""Configuration Django de l'API GRIDD.

Toute la configuration propre à un environnement provient des variables
d'environnement (voir ``.env.example``). Un fichier ``.env`` placé à la racine
de ``apps/api`` est chargé en développement ; en conteneur, les variables sont
fournies par Docker Compose ou l'orchestrateur.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} doit être un entier.") from exc


DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY est obligatoire lorsque DEBUG=false."
        )
    SECRET_KEY = "dev-only-secret-key"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")


INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "channels",
    "core",
]


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"

# Le backend ne sert plus l'interface : seuls l'admin Django et l'API
# navigable utilisent des gabarits (fournis par les applications).
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


if os.getenv("DB_ENGINE", "sqlite").lower() == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "gridd"),
            "USER": os.getenv("DB_USER", "gridd"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5433"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]


LANGUAGE_CODE = "fr-ca"
TIME_ZONE = os.getenv("TIME_ZONE", "America/Toronto")
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Accès depuis le frontend (déployé séparément)
# ---------------------------------------------------------------------------

# Origines autorisées à appeler l'API depuis un navigateur, par exemple
# « https://gridd.example.org,http://localhost:5173 ».
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = False  # authentification par en-tête, pas par cookie

# Origines acceptées pour les WebSocket : hôtes de l'API + origines CORS.
WEBSOCKET_ALLOWED_ORIGINS = ALLOWED_HOSTS + CORS_ALLOWED_ORIGINS
if DEBUG:
    WEBSOCKET_ALLOWED_ORIGINS += ["localhost", "127.0.0.1", "[::1]"]

# Nécessaire pour l'admin Django derrière HTTPS (ex. « https://api.example.org »).
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

if env_bool("USE_X_FORWARDED_PROTO", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SESSION_COOKIE_SECURE = env_bool("SECURE_COOKIES", True)
    CSRF_COOKIE_SECURE = env_bool("SECURE_COOKIES", True)
    SECURE_CONTENT_TYPE_NOSNIFF = True


# ---------------------------------------------------------------------------
# Django Channels
# ---------------------------------------------------------------------------

REDIS_URL = os.getenv("REDIS_URL", "")

if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [
                    {
                        "address": REDIS_URL,
                        "socket_timeout": 15,
                        "socket_connect_timeout": 15,
                    }
                ],
            },
        },
    }
else:
    # Sans Redis, le temps réel ne fonctionne qu'à l'intérieur d'un même
    # processus : le consumer Kafka ou le simulateur ne pourront pas notifier
    # le serveur web. Réservé aux tests et au développement isolé.
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


# ---------------------------------------------------------------------------
# API REST
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.authentication.ExpiringTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Lecture publique (tableau de bord) ; toute écriture exige un compte.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_RENDERER_CLASSES": (
        [
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
        ]
        if DEBUG
        else ["rest_framework.renderers.JSONRenderer"]
    ),
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "login": os.getenv("LOGIN_THROTTLE_RATE", "10/min"),
    },
}

# Durée de validité d'un jeton d'accès (heures).
AUTH_TOKEN_TTL_HOURS = env_int("AUTH_TOKEN_TTL_HOURS", 12)


# ---------------------------------------------------------------------------
# Historique des mesures
# ---------------------------------------------------------------------------

# Étendue maximale d'une requête d'historique (start/end).
HISTORY_MAX_RANGE_DAYS = env_int("HISTORY_MAX_RANGE_DAYS", 31)
# Nombre de points visé lorsque la granularité est choisie automatiquement.
HISTORY_TARGET_POINTS = env_int("HISTORY_TARGET_POINTS", 400)
# Nombre maximal de points lorsqu'une granularité explicite est demandée.
HISTORY_MAX_POINTS = env_int("HISTORY_MAX_POINTS", 3000)


# ---------------------------------------------------------------------------
# Journalisation (sortie standard, exploitée par Docker)
# ---------------------------------------------------------------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "core": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}
