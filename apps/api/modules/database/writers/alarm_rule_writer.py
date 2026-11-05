from modules.database.models import AlarmRule, Zone
from shared.messaging import CommandFailed


class AlarmRuleWriter:
    """Création, modification et suppression des règles d'alarme.

    Les données reçues ont déjà été validées par le module ``alarms`` ; ce
    writer ne fait que les appliquer. La zone est désignée par son code.
    """

    FIELDS = (
        "name",
        "description",
        "zone",
        "metric",
        "operator",
        "threshold",
        "threshold_high",
        "enabled",
        "severity",
        "min_duration_seconds",
        "hysteresis",
    )

    def create(self, fields) -> AlarmRule:
        return AlarmRule.objects.create(**self._model_values(fields))

    def update(self, rule_id, fields) -> tuple[AlarmRule, list[str]]:
        rule = self._get(rule_id)
        values = self._model_values(fields)
        changed = []
        for attribute, value in values.items():
            if getattr(rule, attribute) != value:
                setattr(rule, attribute, value)
                changed.append("zone" if attribute == "zone_id" else attribute)
        rule.save()
        return rule, changed

    def delete(self, rule_id) -> AlarmRule:
        rule = self._get(rule_id)
        rule.delete()
        return rule

    def _get(self, rule_id) -> AlarmRule:
        rule = AlarmRule.objects.filter(pk=rule_id).first()
        if rule is None:
            raise CommandFailed(CommandFailed.NOT_FOUND, "Règle d'alarme introuvable.")
        return rule

    def _model_values(self, fields) -> dict:
        values = {}
        for name in self.FIELDS:
            if name not in fields:
                continue
            if name == "zone":
                values["zone_id"] = self._zone_id(fields["zone"])
            else:
                values[name] = fields[name]
        return values

    @staticmethod
    def _zone_id(code):
        if code is None:
            return None
        zone_id = Zone.objects.filter(code=code, active=True).values_list("id", flat=True).first()
        if zone_id is None:
            raise CommandFailed(CommandFailed.INVALID, "Zone inconnue.", {"zone": ["Zone inconnue ou inactive."]})
        return zone_id
