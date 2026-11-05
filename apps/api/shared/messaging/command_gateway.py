import uuid

from shared.contracts.event_types import EventTypes

from .command_failed import CommandFailed
from .command_timeout import CommandTimeout
from .event import Event


class CommandGateway:
    """Envoi d'une commande à un autre module et attente de sa réponse.

    Requête-réponse corrélée sur Kafka : la commande porte un
    ``correlation_id`` et le topic de réponse ; le module destinataire
    publie ``command.succeeded`` ou ``command.failed`` avec le même
    identifiant. Utilisé par l'API pour les écritures dont le frontend attend
    le résultat (création d'une règle, émission d'un jeton…).
    """

    def __init__(self, publisher, registry, *, reply_topic, timeout, before_send=None):
        self._publisher = publisher
        self._registry = registry
        self._reply_topic = reply_topic
        self._timeout = timeout
        self._before_send = before_send

    def send(self, topic, command_type, payload, *, source, key=None) -> dict:
        if self._before_send is not None:
            self._before_send()
        correlation_id = str(uuid.uuid4())
        future = self._registry.expect(correlation_id)
        command = Event(
            type=command_type,
            payload=payload,
            source=source,
            correlation_id=correlation_id,
            reply_to=self._reply_topic,
        )
        try:
            self._publisher.publish(topic, command, key=key)
            # Bus synchrone : la réponse est déjà arrivée ou n'arrivera jamais.
            reply = future.result(timeout=0 if self._publisher.is_synchronous else self._timeout)
        except TimeoutError as exc:
            raise CommandTimeout(f"Pas de réponse à la commande {command_type}.") from exc
        finally:
            self._registry.discard(correlation_id)

        if reply.type == EventTypes.COMMAND_FAILED:
            raise CommandFailed.from_payload(reply.payload)
        return reply.payload.get("data") or {}
