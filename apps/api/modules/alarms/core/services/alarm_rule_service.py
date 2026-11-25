class AlarmRuleService:
    """Cas d'usage de la gestion des règles d'alarme.

    Lecture : port ``AlarmRuleReader``. Écriture : port ``RuleCommands``
    (commande au module Database, dont la réponse est attendue avant de
    relire la règle enregistrée).
    """

    def __init__(self, repository, commands):
        self._repository = repository
        self._commands = commands

    def search(self, *, zone=None, metric=None, enabled=None):
        flag = {"true": True, "false": False}.get(enabled)
        return self._repository.search(zone=zone, metric=metric, enabled=flag)

    def get(self, rule_id):
        return self._repository.get(rule_id)

    def create(self, fields):
        data = self._commands.create(fields)
        return self._repository.get(data["rule_id"])

    def update(self, rule_id, fields):
        self._commands.update(rule_id, fields)
        return self._repository.get(rule_id)

    def remove(self, rule_id):
        self._commands.remove(rule_id)
