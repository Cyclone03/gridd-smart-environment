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


def env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} doit être un nombre.") from exc


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
    "channels",
    # Noyau partagé (messagerie, contrats, HTTP commun) — pas un module métier.
    "shared.apps.SharedConfig",
    # Modules : chacun autonome, ils ne communiquent que par Kafka.
    "modules.database.apps.DatabaseConfig",
    "modules.ingestion.apps.IngestionConfig",
    "modules.alarms.apps.AlarmsConfig",
    "modules.observations.apps.ObservationsConfig",
    "modules.history.apps.HistoryConfig",
    "modules.realtime.apps.RealtimeConfig",
    "modules.health.apps.HealthConfig",
    "modules.simulator.apps.SimulatorConfig",
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
    # Pas d'authentification pour le moment : l'API est ouverte en lecture
    # et en écriture (à protéger par le réseau ou un proxy en production).
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": (
        [
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
        ]
        if DEBUG
        else ["rest_framework.renderers.JSONRenderer"]
    ),
    "EXCEPTION_HANDLER": "shared.http.api_exception_handler.api_exception_handler",
}


# ---------------------------------------------------------------------------
# Périodes d'analyse historique
# ---------------------------------------------------------------------------

# Étendue maximale d'une requête sur une période (start/end).
HISTORY_MAX_RANGE_DAYS = env_int("HISTORY_MAX_RANGE_DAYS", 31)
# Nombre de points visé lorsque la granularité est choisie automatiquement.
HISTORY_TARGET_POINTS = env_int("HISTORY_TARGET_POINTS", 400)
# Nombre maximal de points lorsqu'une granularité explicite est demandée.
HISTORY_MAX_POINTS = env_int("HISTORY_MAX_POINTS", 3000)


# ---------------------------------------------------------------------------
# Bus d'événements (Kafka)
# ---------------------------------------------------------------------------

# kafka : production — chaque module consomme ses topics (manage.py run_consumers).
# memory : bus synchrone dans le processus — tests et développement sans Kafka.
EVENT_BUS = os.getenv("EVENT_BUS", "memory").strip().lower()


def kafka_connection(prefix, fallback=None):
    """Paramètres d'une connexion Kafka ; une variable absente ou vide reprend ``fallback``."""

    def value(name, default=""):
        fallback_value = fallback[name] if fallback else default
        return os.getenv(f"{prefix}{name.upper()}") or fallback_value

    return {
        "bootstrap_servers": value("bootstrap_servers", "localhost:9092"),
        "security_protocol": value("security_protocol", "PLAINTEXT"),
        "sasl_mechanism": value("sasl_mechanism", "SCRAM-SHA-256"),
        "username": value("username"),
        "password": value("password"),
        "ca_cert_path": value("ca_cert_path"),
    }


# « main » : bus interne des modules. « sensors » : topics des capteurs
# (par défaut le même cluster ; KAFKA_SENSORS_* pour lire le Kafka GRIDD).
_KAFKA_MAIN = kafka_connection("KAFKA_")
KAFKA_CONNECTIONS = {
    "main": _KAFKA_MAIN,
    "sensors": kafka_connection("KAFKA_SENSORS_", fallback=_KAFKA_MAIN),
}

# Topics capteurs (entrée du système) : topic → type de mesure.
KAFKA_SENSOR_TOPICS = {
    os.getenv("KAFKA_TOPIC_TEMPERATURE", "gridd.obs.environmental.temperature"): "temperature",
    os.getenv("KAFKA_TOPIC_HUMIDITY", "gridd.obs.environmental.humidity"): "humidity",
    os.getenv("KAFKA_TOPIC_CO2", "gridd.obs.environmental.co2"): "co2",
    os.getenv("KAFKA_TOPIC_SOUND", "gridd.obs.acoustic.sound_level"): "sound_level",
    os.getenv("KAFKA_TOPIC_OCCUPANCY", "gridd.obs.occupancy.count"): "occupancy",
}

# Topics de sortie des modules (voir docs/events.md).
KAFKA_TOPICS = {
    "ingestion_observations": os.getenv("KAFKA_TOPIC_INGESTION_OBSERVATIONS", "gridd.backend.ingestion.observations"),
    "alarms_events": os.getenv("KAFKA_TOPIC_ALARMS_EVENTS", "gridd.backend.alarms.events"),
    "alarms_commands": os.getenv("KAFKA_TOPIC_ALARMS_COMMANDS", "gridd.backend.alarms.commands"),
    "database_events": os.getenv("KAFKA_TOPIC_DATABASE_EVENTS", "gridd.backend.database.events"),
    "database_replies": os.getenv("KAFKA_TOPIC_DATABASE_REPLIES", "gridd.backend.database.replies"),
}

# Topics que le module Database persiste (vide = topics de sortie des modules métier).
DATABASE_SUBSCRIBED_TOPICS = env_list("DATABASE_SUBSCRIBED_TOPICS") or [
    KAFKA_TOPICS["ingestion_observations"],
    KAFKA_TOPICS["alarms_events"],
    KAFKA_TOPICS["alarms_commands"],
]

# Consumer group de chaque module : « <préfixe>.<module> ».
KAFKA_CONSUMER_GROUP_PREFIX = os.getenv("KAFKA_CONSUMER_GROUP_PREFIX", "gridd-backend")
# Attente de la réponse à une commande (création de règle, connexion…).
KAFKA_COMMAND_TIMEOUT_SECONDS = env_float("KAFKA_COMMAND_TIMEOUT_SECONDS", 10)
KAFKA_PUBLISH_TIMEOUT_SECONDS = env_float("KAFKA_PUBLISH_TIMEOUT_SECONDS", 10)
# Erreur transitoire pendant le traitement d'un message : nouvelles tentatives.
KAFKA_MAX_ATTEMPTS = env_int("KAFKA_MAX_ATTEMPTS", 5)
KAFKA_RETRY_DELAY_SECONDS = env_float("KAFKA_RETRY_DELAY_SECONDS", 2)
# Création des topics internes manquants au démarrage de run_consumers.
KAFKA_AUTO_CREATE_TOPICS = env_bool("KAFKA_AUTO_CREATE_TOPICS", True)
KAFKA_TOPIC_PARTITIONS = env_int("KAFKA_TOPIC_PARTITIONS", 3)
KAFKA_TOPIC_REPLICATION_FACTOR = env_int("KAFKA_TOPIC_REPLICATION_FACTOR", 1)


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
        "modules": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "shared": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}
