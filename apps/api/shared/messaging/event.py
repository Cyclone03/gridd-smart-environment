import json
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone

from .message_rejected import MessageRejected


def _new_id():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Event:
    """Enveloppe des messages échangés entre modules sur Kafka.

    ``payload`` contient les données métier (JSON). ``correlation_id`` et
    ``reply_to`` ne sont renseignés que pour les commandes qui attendent une
    réponse (voir ``CommandGateway``).
    """

    type: str
    payload: dict
    source: str = ""
    event_id: str = field(default_factory=_new_id)
    occurred_at: str = field(default_factory=_now)
    correlation_id: str | None = None
    reply_to: str | None = None

    def encode(self) -> bytes:
        return json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    @classmethod
    def decode(cls, raw: bytes) -> "Event":
        try:
            data = json.loads(raw.decode("utf-8"))
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MessageRejected("Enveloppe d'événement illisible.") from exc
        if not isinstance(data, dict) or not data.get("type") or not isinstance(data.get("payload"), dict):
            raise MessageRejected("Enveloppe d'événement incomplète (type ou payload manquant).")
        known = {item.name for item in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in known})

    def reply(self, reply_type, payload, source) -> "Event":
        """Réponse corrélée à cette commande."""
        return Event(type=reply_type, payload=payload, source=source, correlation_id=self.correlation_id)
