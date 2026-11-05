from dataclasses import dataclass


@dataclass(frozen=True)
class InboundMessage:
    """Message reçu d'un topic, indépendant de la bibliothèque Kafka."""

    topic: str
    value: bytes
    key: bytes | None = None
    partition: int | None = None
    offset: int | None = None
    timestamp_ms: int | None = None
