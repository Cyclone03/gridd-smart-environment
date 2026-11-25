from dataclasses import dataclass


@dataclass(frozen=True)
class PublicationReceipt:
    """Accusé de publication d'un événement du module IA."""

    event_id: str
    topic: str
    zone_code: str | None
