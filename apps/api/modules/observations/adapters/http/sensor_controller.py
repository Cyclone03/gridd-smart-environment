from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from modules.observations.adapters.http.sensor_serializer import SensorSerializer
from modules.observations.composition import sensor_service


class SensorController(viewsets.ViewSet):
    """``/api/sensors/?zone=<code>`` : capteurs actifs."""

    def list(self, request):
        sensors = sensor_service().list(request.query_params.get("zone"))
        return Response(SensorSerializer(sensors, many=True).data)

    def retrieve(self, request, pk=None):
        sensor = sensor_service().get(pk)
        if sensor is None:
            raise NotFound("Capteur introuvable.")
        return Response(SensorSerializer(sensor).data)
