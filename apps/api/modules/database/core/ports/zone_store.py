from typing import Protocol


class ZoneStore(Protocol):
    """Zones (objets exposant ``pk`` et ``code``)."""

    def upsert(self, code, name=None, zone_type=None) -> tuple[object, bool]:
        """``(zone, changed)`` : vrai si la zone est créée, renommée ou retypée."""

    def find(self, code): ...

    def find_active(self, code): ...
