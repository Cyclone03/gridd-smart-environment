from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.observations.serializers.observation_serializer import ObservationSerializer
from modules.observations.serializers.zone_serializer import ZoneSerializer
from modules.observations.services.observation_service import ObservationService


class ZoneLatestController(APIView):
    """``/api/zones/<code>/latest/`` : dernière mesure de chaque type pour une zone."""

    def get(self, request, zone_code):
        result = ObservationService().latest_for_zone(zone_code)
        if result is None:
            raise NotFound("Zone introuvable.")
        zone, latest = result
        return Response(
            {
                "zone": ZoneSerializer(zone).data,
                "latest": {metric: ObservationSerializer(item).data for metric, item in latest.items()},
            }
        )
