from rest_framework import serializers

from modules.alarms.domain.alarm_rule_validator import AlarmRuleValidator
from modules.database.models import AlarmRule, Zone


class AlarmRuleWriteSerializer(serializers.ModelSerializer):
    """Lecture et validation des données d'une règle envoyées par le frontend.

    Ne sauvegarde jamais : les données validées sont transmises au service
    sous forme de commande (``command_fields``). Les règles métier sont
    portées par ``AlarmRuleValidator``. ``zone`` s'échange par code
    (``null`` = toutes les zones).
    """

    validator = AlarmRuleValidator()

    zone = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Zone.objects.filter(active=True),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = AlarmRule
        fields = [
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
        ]
        extra_kwargs = {
            "name": {"error_messages": {"blank": "Le nom est obligatoire."}},
            "min_duration_seconds": {"max_value": AlarmRuleValidator.MAX_DURATION_SECONDS},
        }
        # Contraintes de base vérifiées par le validateur, avec des messages explicites.
        validators = []

    def validate_name(self, value):
        value = value.strip()
        error = self.validator.name_error(value)
        if error:
            raise serializers.ValidationError(error)
        return value

    def validate_metric(self, value):
        error = self.validator.metric_error(value)
        if error:
            raise serializers.ValidationError(error)
        return value

    def validate(self, attrs):
        current = {field: getattr(self.instance, field) for field in self.Meta.fields} if self.instance else {}
        attrs, errors = self.validator.validate(attrs, current)
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def command_fields(self) -> dict:
        """Données validées, prêtes à être publiées (zone désignée par son code)."""
        fields = dict(self.validated_data)
        if "zone" in fields:
            fields["zone"] = fields["zone"].code if fields["zone"] else None
        return fields
