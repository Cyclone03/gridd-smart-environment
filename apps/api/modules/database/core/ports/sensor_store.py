from typing import Protocol


class SensorStore(Protocol):
    """Capteurs (objets exposant ``zone_id``)."""

    def upsert(self, *, node_id, metric, unit, zone, metadata) -> tuple[object, bool]: ...

    def stable_metadata(self, metadata) -> dict:
        """Métadonnées significatives (sans les champs techniques variables)."""
