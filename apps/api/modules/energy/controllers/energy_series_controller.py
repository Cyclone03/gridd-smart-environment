from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.energy.services.energy_query_service import EnergyQueryService


class EnergySeriesController(APIView):
    """``GET /api/energy/zones/<code>/series/`` : énergie estimée par créneau et par usage."""

    def get(self, request, zone_code):
        series = EnergyQueryService().series(zone_code, request.query_params)
        if series is None:
            raise NotFound("Zone introuvable.")
        return Response(series)
