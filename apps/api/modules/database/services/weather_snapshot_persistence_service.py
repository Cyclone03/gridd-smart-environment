import math
from datetime import timedelta
from numbers import Real
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from modules.database.writers.weather_snapshot_writer import WeatherSnapshotWriter
from shared.contracts.event_types import EventTypes
from shared.messaging import Event, MessageRejected


class WeatherSnapshotPersistenceService:
    """Valide et persiste les conditions Open-Meteo émises par le service IA."""

    SOURCE = "ai_prediction_service"
    PROVIDER = "open-meteo"
    REQUIRED_FIELDS = {
        "generated_at",
        "provider",
        "current_at",
        "current_temperature_c",
        "current_relative_humidity_percent",
        "forecast_h1_at",
        "forecast_h1_temperature_c",
        "forecast_h1_relative_humidity_percent",
    }

    def __init__(self, *, snapshot_writer: WeatherSnapshotWriter, producer):
        self._snapshot_writer = snapshot_writer
        self._producer = producer

    def persist(self, event: Event):
        values = self._validated_values(event)
        with transaction.atomic():
            snapshot, created = self._snapshot_writer.create(
                event_id=values.pop("event_id"),
                values=values,
            )
            if not created and not self._matches(snapshot, values):
                raise MessageRejected("Un event_id météo déjà persisté a reçu un contenu différent.")

        if created:
            self._producer.weather_snapshot_persisted(self._event_payload(snapshot))
        return snapshot

    def _validated_values(self, event):
        if event.type != EventTypes.WEATHER_SNAPSHOT_GENERATED:
            raise MessageRejected("Type d'événement météo inattendu.")
        if event.source != self.SOURCE:
            raise MessageRejected("Source d'événement météo invalide.")
        try:
            event_id = UUID(event.event_id)
        except (AttributeError, TypeError, ValueError) as exc:
            raise MessageRejected("event_id doit être un UUID valide.") from exc

        payload = event.payload
        if not isinstance(payload, dict):
            raise MessageRejected("Le payload météo doit être un objet.")
        missing = self.REQUIRED_FIELDS.difference(payload)
        if missing:
            raise MessageRejected(f"Champs manquants dans la météo : {', '.join(sorted(missing))}.")

        if payload["provider"] != self.PROVIDER:
            raise MessageRejected("provider doit être open-meteo.")
        generated_at = self._utc_datetime(payload["generated_at"], "generated_at")
        current_at = self._utc_datetime(payload["current_at"], "current_at")
        forecast_h1_at = self._utc_datetime(payload["forecast_h1_at"], "forecast_h1_at")
        occurred_at = self._utc_datetime(event.occurred_at, "occurred_at")
        if occurred_at != generated_at:
            raise MessageRejected("occurred_at doit correspondre à generated_at.")
        if forecast_h1_at <= current_at or forecast_h1_at <= generated_at:
            raise MessageRejected("forecast_h1_at doit être postérieur à current_at et generated_at.")

        return {
            "event_id": event_id,
            "generated_at": generated_at,
            "provider": self.PROVIDER,
            "current_at": current_at,
            "current_temperature_c": self._finite_number(
                payload["current_temperature_c"],
                "current_temperature_c",
            ),
            "current_relative_humidity_percent": self._humidity(
                payload["current_relative_humidity_percent"],
                "current_relative_humidity_percent",
            ),
            "forecast_h1_at": forecast_h1_at,
            "forecast_h1_temperature_c": self._finite_number(
                payload["forecast_h1_temperature_c"],
                "forecast_h1_temperature_c",
            ),
            "forecast_h1_relative_humidity_percent": self._humidity(
                payload["forecast_h1_relative_humidity_percent"],
                "forecast_h1_relative_humidity_percent",
            ),
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
    def _humidity(cls, value, label):
        converted = cls._finite_number(value, label)
        if not 0 <= converted <= 100:
            raise MessageRejected(f"{label} doit être compris entre 0 et 100.")
        return converted

    @staticmethod
    def _matches(snapshot, values):
        return all(
            getattr(snapshot, field) == value
            for field, value in values.items()
            if field != "event_id"
        )

    @staticmethod
    def _event_payload(snapshot):
        return {
            "weather_snapshot_id": snapshot.pk,
            "weather_snapshot_event_id": str(snapshot.event_id),
            "generated_at": snapshot.generated_at.isoformat(),
            "provider": snapshot.provider,
            "current_at": snapshot.current_at.isoformat(),
            "current_temperature_c": snapshot.current_temperature_c,
            "current_relative_humidity_percent": snapshot.current_relative_humidity_percent,
            "forecast_h1_at": snapshot.forecast_h1_at.isoformat(),
            "forecast_h1_temperature_c": snapshot.forecast_h1_temperature_c,
            "forecast_h1_relative_humidity_percent": snapshot.forecast_h1_relative_humidity_percent,
        }
