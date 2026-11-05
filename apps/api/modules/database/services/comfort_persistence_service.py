from django.db import transaction

from shared.messaging import CommandFailed


class ComfortPersistenceService:
    """Applique les événements et commandes du module ``comfort``."""

    def __init__(self, *, zone_writer, comfort_writer, producer):
        self._zone_writer = zone_writer
        self._comfort_writer = comfort_writer
        self._producer = producer

    def record_assessment(self, payload):
        with transaction.atomic():
            zone = self._zone_writer.find(payload["zone_code"])
            if zone is None:
                return
            assessment, created = self._comfort_writer.record_assessment(zone, payload)
        if created:
            self._producer.comfort_persisted(
                {**payload, "id": assessment.pk, "zone_name": zone.name, "assessed_at": assessment.assessed_at.isoformat()}
            )

    def save_profile(self, payload) -> dict:
        with transaction.atomic():
            self._comfort_writer.save_profile(self._zone(payload["zone_code"]), payload["profile"])
        return {"zone_code": payload["zone_code"]}

    def reset_profile(self, payload) -> dict:
        with transaction.atomic():
            self._comfort_writer.reset_profile(self._zone(payload["zone_code"]))
        return {"zone_code": payload["zone_code"]}

    def _zone(self, code):
        zone = self._zone_writer.find(code)
        if zone is None:
            raise CommandFailed(CommandFailed.NOT_FOUND, "Zone introuvable.")
        return zone
