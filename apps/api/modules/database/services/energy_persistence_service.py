from django.db import transaction

from shared.messaging import CommandFailed


class EnergyPersistenceService:
    """Applique les événements et commandes du module ``energy``."""

    def __init__(self, *, zone_writer, energy_writer, producer):
        self._zone_writer = zone_writer
        self._energy_writer = energy_writer
        self._producer = producer

    def record_estimate(self, payload):
        with transaction.atomic():
            zone = self._zone_writer.find(payload["zone_code"])
            if zone is None:
                return
            estimate, created = self._energy_writer.record_estimate(zone, payload)
        if created:
            self._producer.energy_persisted(
                {"id": estimate.pk, "zone_code": zone.code, "end": payload["end"], "total_wh": estimate.total_wh}
            )

    def save_profile(self, payload) -> dict:
        with transaction.atomic():
            self._energy_writer.save_profile(self._zone(payload["zone_code"]), payload["profile"])
        return {"zone_code": payload["zone_code"]}

    def reset_profile(self, payload) -> dict:
        with transaction.atomic():
            self._energy_writer.reset_profile(self._zone(payload["zone_code"]))
        return {"zone_code": payload["zone_code"]}

    def _zone(self, code):
        zone = self._zone_writer.find(code)
        if zone is None:
            raise CommandFailed(CommandFailed.NOT_FOUND, "Zone introuvable.")
        return zone
