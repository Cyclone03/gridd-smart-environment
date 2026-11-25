from django.utils.dateparse import parse_datetime

from modules.database.models import Observation


class ObservationWriter:
    """Enregistrement des observations validées par le module d'ingestion.

    Adaptateur du port ``ObservationStore``.
    """

    BULK_SIZE = 500

    def create(self, *, event_id, sensor, zone, payload) -> tuple[Observation, bool]:
        """Crée l'observation, sauf si cet événement a déjà été persisté.

        Retourne ``(observation, créée)`` : un message Kafka relivré ne crée
        pas de doublon et n'est pas republié.
        """
        if event_id:
            existing = Observation.objects.filter(event_id=event_id).first()
            if existing is not None:
                return existing, False
        observation = self._build(event_id, sensor, zone, payload)
        observation.save()
        return observation, True

    def create_many(self, items) -> list[Observation]:
        """Crée un lot d'observations ``[(payload, zone, capteur), …]`` en
        deux requêtes (recherche des doublons, insertion groupée).

        Retourne les observations réellement créées, dans l'ordre du lot :
        les événements déjà persistés (messages relivrés) ou présents deux
        fois dans le lot sont ignorés.
        """
        event_ids = [str(payload["event_id"]) for payload, _, _ in items if payload.get("event_id")]
        existing = set()
        if event_ids:
            existing = {
                str(value)
                for value in Observation.objects.filter(event_id__in=event_ids).values_list("event_id", flat=True)
            }
        seen = set()
        observations = []
        for payload, zone, sensor in items:
            event_id = str(payload["event_id"]) if payload.get("event_id") else None
            if event_id:
                if event_id in existing or event_id in seen:
                    continue
                seen.add(event_id)
            observations.append(self._build(event_id, sensor, zone, payload))
        if observations:
            Observation.objects.bulk_create(observations, batch_size=self.BULK_SIZE)
        return observations

    def _build(self, event_id, sensor, zone, payload) -> Observation:
        received_at = self._instant(payload.get("received_at"))
        observation = Observation(
            event_id=event_id or None,
            sensor=sensor,
            zone=zone,
            type=payload["metric"],
            value=payload["value"],
            unit=payload["unit"],
            observed_at=self._instant(payload.get("observed_at")),
            metadata=payload.get("metadata") or {},
            quality_status=payload["quality_status"],
            quality_reason=payload.get("quality_reason") or "",
        )
        if received_at is not None:
            observation.received_at = received_at
        return observation

    @staticmethod
    def _instant(raw):
        return parse_datetime(raw) if raw else None
