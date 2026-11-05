from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from modules.alarms.serializers.alarm_rule_read_serializer import AlarmRuleReadSerializer
from modules.alarms.serializers.alarm_rule_write_serializer import AlarmRuleWriteSerializer
from modules.alarms.services.alarm_rule_catalog_service import AlarmRuleCatalogService
from modules.alarms.services.alarm_rule_service import AlarmRuleService


class AlarmRuleController(viewsets.ViewSet):
    """``/api/alarm-rules/`` : consultation et gestion des règles. Pas de ``PUT``."""

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def list(self, request):
        params = request.query_params
        rules = self._service().search(zone=params.get("zone"), metric=params.get("metric"), enabled=params.get("enabled"))
        return Response(AlarmRuleReadSerializer(rules, many=True).data)

    def retrieve(self, request, pk=None):
        return Response(AlarmRuleReadSerializer(self._get(pk)).data)

    def create(self, request):
        serializer = AlarmRuleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule = self._service().create(serializer.command_fields())
        return Response(AlarmRuleReadSerializer(rule).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        serializer = AlarmRuleWriteSerializer(self._get(pk), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        rule = self._service().update(serializer.instance.pk, serializer.command_fields())
        return Response(AlarmRuleReadSerializer(rule).data)

    def destroy(self, request, pk=None):
        self._service().remove(self._get(pk).pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def metadata(self, request):
        return Response(AlarmRuleCatalogService().describe())

    def _get(self, pk):
        rule = self._service().get(pk)
        if rule is None:
            raise NotFound("Règle d'alarme introuvable.")
        return rule

    @staticmethod
    def _service():
        return AlarmRuleService.build()
