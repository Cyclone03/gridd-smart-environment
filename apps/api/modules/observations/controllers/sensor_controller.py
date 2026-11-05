from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from modules.observations.serializers.sensor_serializer import SensorSerializer
from modules.observations.services.sensor_service import SensorService


class SensorController(viewsets.ViewSet):
    """``/api/sensors/?zone=<code>`` : capteurs actifs."""

    def list(self, request):
        sensors = SensorService().list(request.query_params.get("zone"))
        return Response(SensorSerializer(sensors, many=True).data)

    def retrieve(self, request, pk=None):
        sensor = SensorService().get(pk)
        if sensor is None:
            raise NotFound("Capteur introuvable.")
        return Response(SensorSerializer(sensor).data)
