from typing import Protocol


class ZoneReader(Protocol):
    """Lecture des zones actives."""

    def active(self): ...

    def get(self, zone_id): ...

    def get_by_code(self, code): ...
