from django.http import JsonResponse
from rest_framework.views import APIView

from modules.observations.adapters.http.weather_snapshot_serializer import WeatherSnapshotSerializer
from modules.observations.composition import weather_snapshot_service


class WeatherSnapshotController(APIView):
    """``/api/weather/latest/`` : dernier instantané Open-Meteo."""

    def get(self, request):
        snapshot = weather_snapshot_service().latest()
        payload = WeatherSnapshotSerializer(snapshot).data if snapshot else None
        return JsonResponse(payload, safe=False)
