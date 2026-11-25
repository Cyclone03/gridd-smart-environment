from shared.contracts.topics import Topics
from shared.kernel.events import EventTypes


class RuleCommandGateway:
    """Adaptateur du port ``RuleCommands`` : commandes Kafka corrélées
    (``alarms.commands``) traitées par le module Database."""

    SOURCE = "alarms"

    def __init__(self, gateway):
        self._gateway = gateway

    def create(self, fields):
        return self._send(EventTypes.ALARM_RULE_CREATE, {"fields": fields})

    def update(self, rule_id, fields):
        return self._send(EventTypes.ALARM_RULE_UPDATE, {"rule_id": rule_id, "fields": fields}, key=rule_id)

    def remove(self, rule_id):
        return self._send(EventTypes.ALARM_RULE_DELETE, {"rule_id": rule_id}, key=rule_id)

    def _send(self, command_type, payload, key=None):
        return self._gateway.send(
            Topics.alarms_commands(),
            command_type,
            payload,
            source=self.SOURCE,
            key=f"rule:{key}" if key is not None else None,
        )
