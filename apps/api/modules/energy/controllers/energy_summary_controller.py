from rest_framework.response import Response
from rest_framework.views import APIView

from modules.energy.services.energy_query_service import EnergyQueryService


class EnergySummaryController(APIView):
    """``GET /api/energy/summary/`` : énergie estimée par zone et totale sur une période
    (paramètres identiques à l'historique ; défaut : 24 dernières heures)."""

    def get(self, request):
        return Response(EnergyQueryService().summary(request.query_params))
