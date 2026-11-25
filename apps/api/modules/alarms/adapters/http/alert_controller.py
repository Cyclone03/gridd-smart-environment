from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from modules.alarms.adapters.http.alert_filter_serializer import AlertFilterSerializer
from modules.alarms.adapters.http.alert_serializer import AlertSerializer
from modules.alarms.composition import alert_query_service


class AlertController(viewsets.ViewSet):
    """``/api/alerts/`` : alertes et historique des épisodes d'alarme.

    Filtres : ``active``, ``zone`` (code), ``rule`` (id), ``severity``,
    ``since``, ``until`` (ISO 8601) et ``limit`` (défaut 500, maximum 1 000).
    """

    def list(self, request):
        filters = AlertFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        alerts = alert_query_service().search(**filters.validated_data)
        return Response(AlertSerializer(alerts, many=True).data)

    def retrieve(self, request, pk=None):
        alert = alert_query_service().get(pk)
        if alert is None:
            raise NotFound("Alerte introuvable.")
        return Response(AlertSerializer(alert).data)
