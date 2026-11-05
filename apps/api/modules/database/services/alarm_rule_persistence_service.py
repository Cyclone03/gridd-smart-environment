from django.db import transaction


class AlarmRulePersistenceService:
    """Exécute les commandes de gestion des règles et publie ``alarm_rule.changed``.

    Les conséquences métier d'une modification (clôture des alertes en cours,
    report de gravité) sont décidées par le module ``alarms`` à la réception
    de cet événement.
    """

    def __init__(self, *, rule_writer, producer):
        self._rule_writer = rule_writer
        self._producer = producer

    def create(self, payload) -> dict:
        with transaction.atomic():
            rule = self._rule_writer.create(payload["fields"])
        self._producer.alarm_rule_changed(rule=rule, action="created", changed_fields=[])
        return {"rule_id": rule.pk}

    def update(self, payload) -> dict:
        with transaction.atomic():
            rule, changed_fields = self._rule_writer.update(payload["rule_id"], payload["fields"])
        self._producer.alarm_rule_changed(rule=rule, action="updated", changed_fields=changed_fields)
        return {"rule_id": rule.pk, "changed_fields": changed_fields}

    def delete(self, payload) -> dict:
        rule_id = payload["rule_id"]
        with transaction.atomic():
            rule = self._rule_writer.delete(rule_id)
        rule.pk = rule_id  # ``delete()`` efface la clé primaire de l'instance
        self._producer.alarm_rule_changed(rule=rule, action="deleted", changed_fields=[])
        return {"rule_id": rule_id}
