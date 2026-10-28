"""Gestion des règles d'alarme : ``/api/alarm-rules/``.

Lecture publique ; création, modification et suppression soumises aux
permissions ``core.add_alarmrule``, ``core.change_alarmrule`` et
``core.delete_alarmrule`` (groupe « Gestionnaires des alarmes »).
"""

from django.db import transaction
from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import metrics
from .alarm_engine import delete_rule, on_rule_changed
from .models import AlarmRule, Alert
from .permissions import PublicReadModelPermissions
from .serializers import AlarmRuleSerializer


class AlarmRuleViewSet(viewsets.ModelViewSet):
    serializer_class = AlarmRuleSerializer
    permission_classes = [PublicReadModelPermissions]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = AlarmRule.objects.select_related("zone", "created_by", "updated_by").annotate(
            active_alerts=Count("alerts", filter=Q(alerts__active=True)),
        )
        params = self.request.query_params
        zone = params.get("zone")
        if zone == "all":
            qs = qs.filter(zone__isnull=True)
        elif zone:
            qs = qs.filter(Q(zone__code=zone) | Q(zone__isnull=True))
        if params.get("metric"):
            qs = qs.filter(metric=params["metric"])
        if params.get("enabled") in {"true", "false"}:
            qs = qs.filter(enabled=params["enabled"] == "true")
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        before = {field: getattr(instance, field) for field in serializer.validated_data}
        with transaction.atomic():
            rule = serializer.save(updated_by=self.request.user)
            changed = [field for field, value in before.items() if getattr(rule, field) != value]
            on_rule_changed(rule, changed)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        # Recharger l'annotation ``active_alerts`` après d'éventuelles résolutions.
        response.data = self.get_serializer(self.get_queryset().get(pk=kwargs["pk"])).data
        return response

    def perform_destroy(self, instance):
        delete_rule(instance)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def metadata(self, request):
        """Catalogue utilisé par le formulaire : mesures, opérateurs, gravités."""
        return Response(
            {
                "metrics": [
                    {
                        "key": definition.key,
                        "label": definition.label,
                        "unit": definition.unit,
                        "integer": definition.integer,
                        "min": definition.plausible_range[0] if definition.plausible_range else None,
                        "max": definition.plausible_range[1] if definition.plausible_range else None,
                        "operators": list(definition.operators),
                    }
                    for definition in metrics.METRICS.values()
                ],
                "operators": [
                    {
                        "key": key,
                        "label": metrics.OPERATOR_LABELS[key],
                        "symbol": metrics.OPERATOR_SYMBOLS.get(key),
                        "range": key in metrics.RANGE_OPERATORS,
                    }
                    for key in metrics.ALL_OPERATORS
                ],
                "severities": [{"key": key, "label": label} for key, label in Alert.Severity.choices],
                "max_duration_seconds": 86400,
            }
        )
