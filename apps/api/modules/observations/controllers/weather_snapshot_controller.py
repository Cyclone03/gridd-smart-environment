from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.views import APIView

from modules.observations.serializers.weather_snapshot_serializer import WeatherSnapshotSerializer
from modules.observations.services.weather_snapshot_service import WeatherSnapshotService


class WeatherSnapshotController(APIView):
    """``/api/weather/latest/`` : dernier instantané Open-Meteo."""

    def get(self, request):
        snapshot = WeatherSnapshotService().latest()
        payload = WeatherSnapshotSerializer(snapshot).data if snapshot else None
        return JsonResponse(payload, safe=False)
