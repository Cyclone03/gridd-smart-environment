from rest_framework import serializers

from . import metrics
from .alarm_engine import describe_rule
from .models import AlarmRule, Alert, Observation, Sensor, ThresholdProfile, Zone


class ThresholdProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThresholdProfile
        exclude = ["id", "zone"]


class ZoneSerializer(serializers.ModelSerializer):
    threshold_profile = ThresholdProfileSerializer(read_only=True)
    # Types de mesure réellement disponibles (capteurs actifs) : le frontend
    # n'a plus à déduire les mesures d'un espace à partir de son nom.
    metrics = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = [
            "id",
            "name",
            "code",
            "zone_type",
            "description",
            "active",
            "metrics",
            "threshold_profile",
        ]

    def get_metrics(self, zone):
        # ``active_sensors`` est préchargé par ZoneViewSet ; repli sinon.
        sensors = getattr(zone, "active_sensors", None)
        if sensors is None:
            sensors = zone.sensors.filter(active=True)
        order = list(metrics.METRICS)
        types = {sensor.sensor_type for sensor in sensors}
        return sorted(types, key=lambda key: order.index(key) if key in order else len(order))


class SensorSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True)

    class Meta:
        model = Sensor
        fields = "__all__"


class ObservationSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    sensor_node_id = serializers.CharField(source="sensor.node_id", read_only=True)

    class Meta:
        model = Observation
        fields = "__all__"


class AlertSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    rule_name = serializers.CharField(source="rule.name", read_only=True, default=None)

    class Meta:
        model = Alert
        fields = [
            "id",
            "zone",
            "zone_code",
            "zone_name",
            "observation",
            "rule",
            "rule_name",
            "code",
            "message",
            "severity",
            "trigger_value",
            "created_at",
            "resolved_at",
            "resolution",
            "active",
        ]


class AlarmRuleSerializer(serializers.ModelSerializer):
    """Lecture et écriture d'une règle d'alarme.

    ``zone`` s'échange par code de zone (``null`` = toutes les zones). ``unit``
    est déduite du type de mesure et n'est pas modifiable.
    """

    zone = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Zone.objects.filter(active=True),
        allow_null=True,
        required=False,
    )
    zone_name = serializers.CharField(source="zone.name", read_only=True, default=None)
    unit = serializers.CharField(read_only=True)
    condition_label = serializers.SerializerMethodField()
    active_alerts = serializers.IntegerField(read_only=True, default=0)
    created_by = serializers.CharField(source="created_by.get_username", read_only=True, default=None)
    updated_by = serializers.CharField(source="updated_by.get_username", read_only=True, default=None)

    class Meta:
        model = AlarmRule
        fields = [
            "id",
            "name",
            "description",
            "zone",
            "zone_name",
            "metric",
            "operator",
            "threshold",
            "threshold_high",
            "unit",
            "condition_label",
            "enabled",
            "severity",
            "min_duration_seconds",
            "hysteresis",
            "active_alerts",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {
            "name": {"error_messages": {"blank": "Le nom est obligatoire."}},
            "min_duration_seconds": {"max_value": 86400},
        }
        # Les contraintes de base sont validées ci-dessous avec des messages
        # explicites plutôt que par les CheckConstraint du modèle.
        validators = []

    def get_condition_label(self, rule):
        return describe_rule(rule)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Le nom est obligatoire.")
        return value

    def validate_metric(self, value):
        if metrics.get_metric(value) is None:
            raise serializers.ValidationError("Type de mesure inconnu.")
        return value

    def validate(self, attrs):
        def current(field, default=None):
            if field in attrs:
                return attrs[field]
            if self.instance is not None:
                return getattr(self.instance, field)
            return default

        metric_key = current("metric")
        operator = current("operator")
        low = current("threshold")
        high = current("threshold_high")
        hysteresis = current("hysteresis", 0) or 0
        definition = metrics.get_metric(metric_key)
        errors = {}

        if definition and operator and operator not in definition.operators:
            errors["operator"] = "Cet opérateur n'est pas disponible pour ce type de mesure."

        if operator in metrics.RANGE_OPERATORS:
            if high is None:
                errors["threshold_high"] = "La borne haute est obligatoire pour un intervalle."
            elif low is not None and high <= low:
                errors["threshold_high"] = "La borne haute doit être supérieure à la borne basse."
            elif low is not None and operator == metrics.OPERATOR_OUTSIDE_RANGE and 2 * hysteresis >= high - low:
                errors["hysteresis"] = "L'hystérésis doit être inférieure à la moitié de l'intervalle."
        elif "threshold_high" in attrs and high is not None:
            errors["threshold_high"] = "Une seule valeur seuil est attendue pour cet opérateur."
        elif operator and "operator" in attrs:
            # Passage d'un intervalle à un seuil simple : on efface la borne haute.
            attrs["threshold_high"] = None

        if hysteresis < 0:
            errors["hysteresis"] = "L'hystérésis doit être positive ou nulle."

        if definition:
            bounds = definition.plausible_range
            for field, value in (("threshold", low), ("threshold_high", high)):
                if value is None or field in errors:
                    continue
                if bounds and not bounds[0] <= value <= bounds[1]:
                    errors[field] = (
                        f"Valeur hors des limites physiques du capteur "
                        f"({bounds[0]} à {bounds[1]} {definition.unit})."
                    )
                elif definition.integer and float(value) != int(value):
                    errors[field] = "Ce paramètre est un comptage : utilisez un nombre entier."
            if definition.integer and float(hysteresis) != int(hysteresis) and "hysteresis" not in errors:
                errors["hysteresis"] = "Ce paramètre est un comptage : utilisez un nombre entier."

        if errors:
            raise serializers.ValidationError(errors)
        return attrs
