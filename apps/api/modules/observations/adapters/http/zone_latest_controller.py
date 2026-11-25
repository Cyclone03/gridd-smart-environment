from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.observations.adapters.http.observation_serializer import ObservationSerializer
from modules.observations.adapters.http.zone_serializer import ZoneSerializer
from modules.observations.composition import observation_service


class ZoneLatestController(APIView):
    """``/api/zones/<code>/latest/`` : dernière mesure de chaque type pour une zone."""

    def get(self, request, zone_code):
        result = observation_service().latest_for_zone(zone_code)
        if result is None:
            raise NotFound("Zone introuvable.")
        zone, latest = result
        return Response(
            {
                "zone": ZoneSerializer(zone).data,
                "latest": {metric: ObservationSerializer(item).data for metric, item in latest.items()},
            }
        )
