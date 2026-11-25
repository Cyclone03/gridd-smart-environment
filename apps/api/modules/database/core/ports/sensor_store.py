from typing import Protocol


class SensorStore(Protocol):
    """Capteurs, un par zone et par type de mesure (objets exposant ``zone_id``)."""

    def upsert(self, *, sensor, metric, unit, zone, metadata) -> tuple[object, bool]:
        """``(capteur, created)`` ; ``sensor`` : identifiant zone + mesure."""

    def stable_metadata(self, metadata) -> dict:
        """Métadonnées significatives (sans les champs techniques variables)."""
