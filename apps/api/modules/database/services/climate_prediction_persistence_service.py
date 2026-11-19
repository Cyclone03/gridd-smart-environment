import math
from datetime import timedelta
from numbers import Real
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from modules.database.models import ClimatePrediction, Zone
from modules.database.writers.climate_prediction_writer import ClimatePredictionWriter
from shared.contracts.event_types import EventTypes
from shared.messaging import Event, MessageRejected


class ClimatePredictionPersistenceService:
    """Valide et persiste les prédictions reçues par le module Database."""

    SOURCE = "ai_prediction_service"
    REQUIRED_FIELDS = {
        "zone_code",
        "generated_at",
        "target_at",
        "predicted_temperature_c",
        "predicted_humidity_percent",
        "model_version",
        "prediction_mode",
    }

    def __init__(self, *, prediction_writer, producer):
        self._prediction_writer = prediction_writer
        self._producer = producer

    def persist(self, event: Event):
        values = self._validated_values(event)

        with transaction.atomic():
            zone = Zone.objects.filter(code=values.pop("zone_code"), active=True).first()
            if zone is None:
                raise MessageRejected("Zone de prédiction inconnue ou inactive.")
            prediction, created = self._prediction_writer.create(
                event_id=values.pop("event_id"),
                zone=zone,
                values=values,
            )
            if not created and not self._matches(prediction, zone, values):
                raise MessageRejected(
                    "Un event_id de prédiction déjà persisté a reçu un contenu différent."
                )

        if created:
            self._producer.climate_prediction_persisted(self._event_payload(prediction))
        return prediction

    def _validated_values(self, event):
        if event.type != EventTypes.CLIMATE_PREDICTION_GENERATED:
            raise MessageRejected("Type d'événement de prédiction inattendu.")
        if event.source != self.SOURCE:
            raise MessageRejected("Source d'événement de prédiction invalide.")
        try:
            event_id = UUID(event.event_id)
        except (AttributeError, TypeError, ValueError) as exc:
            raise MessageRejected("event_id doit être un UUID valide.") from exc

        payload = event.payload
        if not isinstance(payload, dict):
            raise MessageRejected("Le payload de prédiction doit être un objet.")
        missing = self.REQUIRED_FIELDS.difference(payload)
        if missing:
            raise MessageRejected(
                f"Champs manquants dans la prédiction : {', '.join(sorted(missing))}."
            )

        zone_code = payload["zone_code"]
        if not isinstance(zone_code, str) or not zone_code.strip():
            raise MessageRejected("zone_code doit être une chaîne non vide.")
        zone_code = zone_code.strip()

        generated_at = self._utc_datetime(payload["generated_at"], "generated_at")
        target_at = self._utc_datetime(payload["target_at"], "target_at")
        occurred_at = self._utc_datetime(event.occurred_at, "occurred_at")
        if occurred_at != generated_at:
            raise MessageRejected("occurred_at doit correspondre à generated_at.")
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
        if prediction_mode not in ClimatePrediction.PredictionMode.values:
            raise MessageRejected("prediction_mode doit être experimental ou operational.")

        return {
            "event_id": event_id,
            "zone_code": zone_code,
            "generated_at": generated_at,
            "target_at": target_at,
            "predicted_temperature_c": self._finite_number(
                payload["predicted_temperature_c"], "predicted_temperature_c"
            ),
            "predicted_humidity_percent": self._finite_number(
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

    @staticmethod
    def _matches(prediction, zone, values):
        return (
            prediction.zone_id == zone.pk
            and prediction.generated_at == values["generated_at"]
            and prediction.target_at == values["target_at"]
            and prediction.predicted_temperature_c == values["predicted_temperature_c"]
            and prediction.predicted_humidity_percent == values["predicted_humidity_percent"]
            and prediction.model_version == values["model_version"]
            and prediction.prediction_mode == values["prediction_mode"]
        )

    @staticmethod
    def _event_payload(prediction):
        return {
            "prediction_id": prediction.pk,
            "prediction_event_id": str(prediction.event_id),
            "zone_code": prediction.zone.code,
            "generated_at": prediction.generated_at.isoformat(),
            "target_at": prediction.target_at.isoformat(),
            "predicted_temperature_c": prediction.predicted_temperature_c,
            "predicted_humidity_percent": prediction.predicted_humidity_percent,
            "model_version": prediction.model_version,
            "prediction_mode": prediction.prediction_mode,
        }
