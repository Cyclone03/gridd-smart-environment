from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.history.services.history_service import HistoryService


class ZoneHistoryController(APIView):
    """``/api/zones/<code>/history/`` — voir docs/api.md pour les paramètres."""

    def get(self, request, zone_code):
        history = HistoryService().history(zone_code, request.query_params)
        if history is None:
            raise NotFound("Zone introuvable.")
        return Response(history)
