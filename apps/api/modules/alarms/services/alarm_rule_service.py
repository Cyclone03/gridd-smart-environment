from modules.alarms.repositories.alarm_rule_repository import AlarmRuleRepository
from shared.contracts.event_types import EventTypes
from shared.contracts.topics import Topics
from shared.messaging import Messaging


class AlarmRuleService:
    """Cas d'usage de la gestion des règles d'alarme.

    Lecture : depuis la base, via le repository du module. Écriture :
    commande Kafka au module Database, dont la réponse est attendue avant de
    relire la règle enregistrée.
    """

    SOURCE = "alarms"

    def __init__(self, repository, gateway):
        self._repository = repository
        self._gateway = gateway

    @classmethod
    def build(cls):
        return cls(AlarmRuleRepository(), Messaging.current().gateway())

    def search(self, *, zone=None, metric=None, enabled=None):
        flag = {"true": True, "false": False}.get(enabled)
        return self._repository.search(zone=zone, metric=metric, enabled=flag)

    def get(self, rule_id):
        return self._repository.get(rule_id)

    def create(self, fields):
        data = self._send(EventTypes.ALARM_RULE_CREATE, {"fields": fields})
        return self._repository.get(data["rule_id"])

    def update(self, rule_id, fields):
        self._send(EventTypes.ALARM_RULE_UPDATE, {"rule_id": rule_id, "fields": fields}, key=rule_id)
        return self._repository.get(rule_id)

    def remove(self, rule_id):
        self._send(EventTypes.ALARM_RULE_DELETE, {"rule_id": rule_id}, key=rule_id)

    def _send(self, command_type, payload, key=None):
        return self._gateway.send(
            Topics.alarms_commands(),
            command_type,
            payload,
            source=self.SOURCE,
            key=f"rule:{key}" if key is not None else None,
        )
