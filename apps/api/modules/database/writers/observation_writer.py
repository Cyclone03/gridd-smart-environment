from django.utils.dateparse import parse_datetime

from modules.database.models import Observation


class ObservationWriter:
    """Enregistrement des observations validées par le module d'ingestion."""

    def create(self, *, event_id, sensor, zone, payload) -> tuple[Observation, bool]:
        """Crée l'observation, sauf si cet événement a déjà été persisté.

        Retourne ``(observation, créée)`` : un message Kafka relivré ne crée
        pas de doublon et n'est pas republié.
        """
        if event_id:
            existing = Observation.objects.filter(event_id=event_id).first()
            if existing is not None:
                return existing, False

        observation = Observation.objects.create(
            event_id=event_id or None,
            sensor=sensor,
            zone=zone,
            type=payload["metric"],
            value=payload["value"],
            unit=payload["unit"],
            observed_at=self._instant(payload.get("observed_at")),
            received_at=self._instant(payload.get("received_at")),
            metadata=payload.get("metadata") or {},
            quality_status=payload["quality_status"],
            quality_reason=payload.get("quality_reason") or "",
        )
        return observation, True

    @staticmethod
    def _instant(raw):
        return parse_datetime(raw) if raw else None
