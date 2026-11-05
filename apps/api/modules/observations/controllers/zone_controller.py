from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from modules.observations.serializers.zone_serializer import ZoneSerializer
from modules.observations.services.zone_service import ZoneService


class ZoneController(viewsets.ViewSet):
    """``/api/zones/`` : zones actives, triées par nom."""

    def list(self, request):
        return Response(ZoneSerializer(ZoneService().list(), many=True).data)

    def retrieve(self, request, pk=None):
        zone = ZoneService().get(pk)
        if zone is None:
            raise NotFound("Zone introuvable.")
        return Response(ZoneSerializer(zone).data)
