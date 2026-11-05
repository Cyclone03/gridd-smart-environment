from rest_framework.response import Response
from rest_framework.views import APIView

from modules.comfort.serializers.zone_comfort_serializer import ZoneComfortSerializer
from modules.comfort.services.comfort_query_service import ComfortQueryService


class ComfortCurrentController(APIView):
    """``GET /api/comfort/current/`` : confort actuel de chaque zone active."""

    def get(self, request):
        return Response(ZoneComfortSerializer(ComfortQueryService().current(), many=True).data)
