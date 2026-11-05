from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from modules.observations.serializers.observation_serializer import ObservationSerializer
from modules.observations.services.observation_service import ObservationService


class ObservationController(viewsets.ViewSet):
    """``/api/observations/?zone=<code>&type=<type>`` : 1 000 dernières observations ;
    ``/api/observations/latest/`` : dernière observation de chaque zone et type."""

    def list(self, request):
        params = request.query_params
        observations = ObservationService().feed(zone_code=params.get("zone"), metric=params.get("type"))
        return Response(ObservationSerializer(observations, many=True).data)

    def retrieve(self, request, pk=None):
        observation = ObservationService().get(pk)
        if observation is None:
            raise NotFound("Observation introuvable.")
        return Response(ObservationSerializer(observation).data)

    @action(detail=False, methods=["get"])
    def latest(self, request):
        return Response(ObservationSerializer(ObservationService().latest(), many=True).data)
