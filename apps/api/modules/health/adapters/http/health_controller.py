from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.health.composition import health_service


class HealthController(APIView):
    """``GET /api/health/`` : 200 si la base répond, 503 sinon (Docker, supervision)."""

    def get(self, request):
        body, healthy = health_service().check()
        return Response(body, status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE)
