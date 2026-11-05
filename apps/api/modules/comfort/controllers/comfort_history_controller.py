from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.comfort.services.comfort_query_service import ComfortQueryService


class ComfortHistoryController(APIView):
    """``GET /api/comfort/zones/<code>/history/`` : score et niveaux de confort par créneau.

    Paramètres de période identiques à l'historique des mesures.
    """

    def get(self, request, zone_code):
        history = ComfortQueryService().history(zone_code, request.query_params)
        if history is None:
            raise NotFound("Zone introuvable.")
        return Response(history)
