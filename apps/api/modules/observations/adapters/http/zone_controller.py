from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from modules.observations.adapters.http.zone_serializer import ZoneSerializer
from modules.observations.composition import zone_service


class ZoneController(viewsets.ViewSet):
    """``/api/zones/`` : zones actives, triées par nom."""

    def list(self, request):
        return Response(ZoneSerializer(zone_service().list(), many=True).data)

    def retrieve(self, request, pk=None):
        zone = zone_service().get(pk)
        if zone is None:
            raise NotFound("Zone introuvable.")
        return Response(ZoneSerializer(zone).data)
