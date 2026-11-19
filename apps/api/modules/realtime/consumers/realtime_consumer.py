import logging
import math
from datetime import timedelta
from numbers import Real
from uuid import UUID

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from modules.realtime.services.dashboard_snapshot_service import DashboardSnapshotService
from modules.realtime.services.realtime_broadcaster import RealtimeBroadcaster
from shared.contracts.event_types import EventTypes
from shared.messaging import EventHandler, MessageRejected

logger = logging.getLogger(__name__)

GRIDD_ZONE_CODES = frozenset(
    {
        "open-workspace",
        "server-equipment-room",
        "professors-office",
        "individual-work-cubicle-01",
        "meeting-room",
        "individual-work-cubicle-02",
    }
)


class RealtimeConsumer(EventHandler):
    """Relaie aux navigateurs les faits persistés par le module Database :
    les tableaux de bord ne reçoivent que des données réellement enregistrées.

    Pour ``alerts.changed`` et ``zones.changed``, la nouvelle liste est lue une
    seule fois ici puis diffusée à tous les navigateurs connectés (au lieu que
    chaque navigateur la redemande à l'API REST).
    """

    # Au-delà, une mesure relayée est un rattrapage et n'est pas diffusée une à une.
    LIVE_WINDOW = timedelta(minutes=2)
    PREDICTION_MODES = frozenset({"experimental", "operational"})
    PREDICTION_FIELDS = frozenset(
        {
            "prediction_id",
            "prediction_event_id",
            "zone_code",
            "generated_at",
            "target_at",
            "predicted_temperature_c",
            "predicted_humidity_percent",
            "model_version",
            "prediction_mode",
        }
    )
    WEATHER_SNAPSHOT_FIELDS = frozenset(
        {
            "weather_snapshot_id",
            "weather_snapshot_event_id",
            "generated_at",
            "provider",
            "current_at",
            "current_temperature_c",
            "current_relative_humidity_percent",
            "forecast_h1_at",
            "forecast_h1_temperature_c",
            "forecast_h1_relative_humidity_percent",
        }
    )

    def __init__(self, broadcaster, snapshots):
        self._broadcaster = broadcaster
        self._snapshots = snapshots
        # Pendant un lot Kafka : une seule relecture/diffusion par type à la fin.
        self._batching = False
        self._pending = set()
        self._observations = []

    @classmethod
    def build(cls):
        return cls(RealtimeBroadcaster(), DashboardSnapshotService())

    def routes(self):
        return {
            EventTypes.OBSERVATION_PERSISTED: lambda event: self._observation(event.payload),
            EventTypes.CLIMATE_PREDICTION_PERSISTED: self._prediction,
            EventTypes.WEATHER_SNAPSHOT_PERSISTED: self._weather_snapshot,
            EventTypes.ALERTS_CHANGED: lambda event: self._changed("alerts"),
            EventTypes.ZONES_CHANGED: lambda event: self._changed("zones"),
        }

    def begin_batch(self):
        self._batching = True

    def end_batch(self):
        self._batching = False
        observations, self._observations = self._observations, []
        if observations:
            self._broadcaster.observations_created(self.coalesce(observations))
        pending, self._pending = self._pending, set()
        for kind in sorted(pending):
            self._broadcast(kind)

    def _observation(self, payload):
        if self._batching:
            self._observations.append(payload)
        else:
            self._broadcaster.observation_created(payload)

    def _prediction(self, event):
        if event.source != "database":
            raise MessageRejected("Source invalide pour une prédiction persistée.")
        payload = self._validated_prediction(event.payload)
        self._broadcaster.climate_prediction_created(payload)

    def _weather_snapshot(self, event):
        if event.source != "database":
            raise MessageRejected("Source invalide pour un instantané météo persisté.")
        payload = self._validated_weather_snapshot(event.payload)
        self._broadcaster.weather_snapshot_created(payload)

    @classmethod
    def _validated_weather_snapshot(cls, payload):
        if not isinstance(payload, dict):
            raise MessageRejected("Le payload météo doit être un objet.")
        missing = cls.WEATHER_SNAPSHOT_FIELDS.difference(payload)
        if missing:
            raise MessageRejected(
                f"Champs manquants dans l'instantané météo : {', '.join(sorted(missing))}."
            )

        snapshot_id = payload["weather_snapshot_id"]
        if isinstance(snapshot_id, bool) or not isinstance(snapshot_id, int) or snapshot_id <= 0:
            raise MessageRejected("weather_snapshot_id doit être un entier positif.")

        try:
            event_id = str(UUID(payload["weather_snapshot_event_id"]))
        except (AttributeError, TypeError, ValueError) as exc:
            raise MessageRejected("weather_snapshot_event_id doit être un UUID valide.") from exc

        if payload["provider"] != "open-meteo":
            raise MessageRejected("provider météo invalide.")
        generated_at = cls._utc_datetime(payload["generated_at"], "generated_at")
        current_at = cls._utc_datetime(payload["current_at"], "current_at")
        forecast_h1_at = cls._utc_datetime(payload["forecast_h1_at"], "forecast_h1_at")
        if forecast_h1_at <= current_at or forecast_h1_at <= generated_at:
            raise MessageRejected("forecast_h1_at doit être postérieur à current_at et generated_at.")

        current_humidity = cls._finite_number(
            payload["current_relative_humidity_percent"],
            "current_relative_humidity_percent",
        )
        forecast_humidity = cls._finite_number(
            payload["forecast_h1_relative_humidity_percent"],
            "forecast_h1_relative_humidity_percent",
        )
        if not 0 <= current_humidity <= 100 or not 0 <= forecast_humidity <= 100:
            raise MessageRejected("L'humidité météo doit être comprise entre 0 et 100.")

        return {
            "weather_snapshot_id": snapshot_id,
            "weather_snapshot_event_id": event_id,
            "generated_at": generated_at.isoformat(),
            "provider": "open-meteo",
            "current_at": current_at.isoformat(),
            "current_temperature_c": cls._finite_number(
                payload["current_temperature_c"],
                "current_temperature_c",
            ),
            "current_relative_humidity_percent": current_humidity,
            "forecast_h1_at": forecast_h1_at.isoformat(),
            "forecast_h1_temperature_c": cls._finite_number(
                payload["forecast_h1_temperature_c"],
                "forecast_h1_temperature_c",
            ),
            "forecast_h1_relative_humidity_percent": forecast_humidity,
        }

    @classmethod
    def _validated_prediction(cls, payload):
        if not isinstance(payload, dict):
            raise MessageRejected("Le payload de prédiction doit être un objet.")
        missing = cls.PREDICTION_FIELDS.difference(payload)
        if missing:
            raise MessageRejected(
                f"Champs manquants dans la prédiction persistée : {', '.join(sorted(missing))}."
            )

        prediction_id = payload["prediction_id"]
        if isinstance(prediction_id, bool) or not isinstance(prediction_id, int) or prediction_id <= 0:
            raise MessageRejected("prediction_id doit être un entier positif.")

        try:
            prediction_event_id = str(UUID(payload["prediction_event_id"]))
        except (AttributeError, TypeError, ValueError) as exc:
            raise MessageRejected("prediction_event_id doit être un UUID valide.") from exc

        zone_code = payload["zone_code"]
        if not isinstance(zone_code, str) or zone_code not in GRIDD_ZONE_CODES:
            raise MessageRejected("zone_code ne correspond pas à une zone GRIDD connue.")

        generated_at = cls._utc_datetime(payload["generated_at"], "generated_at")
        target_at = cls._utc_datetime(payload["target_at"], "target_at")
        if target_at <= generated_at:
            raise MessageRejected("target_at doit être postérieur à generated_at.")

        model_version = payload["model_version"]
        if (
            not isinstance(model_version, str)
            or not model_version.strip()
            or len(model_version.strip()) > 255
        ):
            raise MessageRejected("model_version doit contenir de 1 à 255 caractères.")

        prediction_mode = payload["prediction_mode"]
        if not isinstance(prediction_mode, str) or prediction_mode not in cls.PREDICTION_MODES:
            raise MessageRejected("prediction_mode doit être experimental ou operational.")

        return {
            "prediction_id": prediction_id,
            "prediction_event_id": prediction_event_id,
            "zone_code": zone_code,
            "generated_at": generated_at.isoformat(),
            "target_at": target_at.isoformat(),
            "predicted_temperature_c": cls._finite_number(
                payload["predicted_temperature_c"], "predicted_temperature_c"
            ),
            "predicted_humidity_percent": cls._finite_number(
                payload["predicted_humidity_percent"], "predicted_humidity_percent"
            ),
            "model_version": model_version.strip(),
            "prediction_mode": prediction_mode,
        }

    @staticmethod
    def _utc_datetime(value, label):
        if not isinstance(value, str):
            raise MessageRejected(f"{label} doit être une date ISO 8601 UTC.")
        try:
            parsed = parse_datetime(value)
        except ValueError as exc:
            raise MessageRejected(f"{label} est une date invalide.") from exc
        if (
            parsed is None
            or not timezone.is_aware(parsed)
            or parsed.utcoffset() != timedelta(0)
        ):
            raise MessageRejected(f"{label} doit être une date ISO 8601 UTC.")
        return parsed

    @staticmethod
    def _finite_number(value, label):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise MessageRejected(f"{label} doit être une valeur numérique.")
        try:
            converted = float(value)
        except (OverflowError, ValueError) as exc:
            raise MessageRejected(f"{label} doit être une valeur finie.") from exc
        if not math.isfinite(converted):
            raise MessageRejected(f"{label} doit être une valeur finie.")
        return converted

    @classmethod
    def coalesce(cls, observations, now=None):
        """Mesures à diffuser pour un lot.

        Les mesures récentes sont toutes gardées (graphiques en direct). Les
        anciennes (rattrapage d'un arriéré) sont réduites à la plus récente
        par capteur et par mesure : diffuser des milliers de valeurs passées
        saturait les files des navigateurs (« channels over capacity ») sans
        rien apporter à l'affichage.
        """
        limit = (now or timezone.now()) - cls.LIVE_WINDOW
        fresh, latest = [], {}
        for payload in observations:
            moment = parse_datetime(payload.get("observed_at") or payload.get("received_at") or "")
            if moment is not None and moment >= limit:
                fresh.append(payload)
                continue
            key = (payload.get("zone_code"), payload.get("sensor"), payload.get("type"))
            known = latest.get(key)
            if known is None or (payload.get("observed_at") or "") >= (known.get("observed_at") or ""):
                latest[key] = payload
        return [*latest.values(), *fresh]

    def _changed(self, kind):
        # Une rafale de changements (ex. 90 alerts.changed en 20 s) ne donne
        # qu'une lecture en base et une diffusion par lot.
        if self._batching:
            self._pending.add(kind)
        else:
            self._broadcast(kind)

    def _broadcast(self, kind):
        if kind == "alerts":
            self._relay(self._snapshots.alerts, self._broadcaster.alerts_changed)
        else:
            self._relay(self._snapshots.zones, self._broadcaster.zones_changed)

    @staticmethod
    def _relay(read, broadcast):
        try:
            payload = read()
        except Exception:
            # Base indisponible : les navigateurs se resynchroniseront à la
            # prochaine connexion (snapshot) ou au prochain changement.
            logger.exception("Lecture impossible pour la diffusion temps réel.")
            return
        broadcast(payload)
