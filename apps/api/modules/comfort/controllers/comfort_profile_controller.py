from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from modules.comfort.domain.comfort_profile import ComfortProfile
from modules.comfort.serializers.comfort_profile_update_serializer import ComfortProfileUpdateSerializer
from modules.comfort.serializers.zone_comfort_serializer import ZoneComfortSerializer
from modules.comfort.services.comfort_profile_service import ComfortProfileService


class ComfortProfileController(viewsets.ViewSet):
    """``/api/comfort/profiles/`` : plages de confort par zone.

    ``PATCH`` personnalise une zone, ``DELETE`` rétablit les valeurs par défaut.
    """

    lookup_field = "zone_code"
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def list(self, request):
        return Response([self._present(zone) for zone in self._service().list()])

    def retrieve(self, request, zone_code=None):
        return Response(self._present(self._get(zone_code)))

    def partial_update(self, request, zone_code=None):
        zone = self._get(zone_code)
        serializer = ComfortProfileUpdateSerializer(data=request.data, partial=True, context={"current": zone.profile})
        serializer.is_valid(raise_exception=True)
        profile = ComfortProfile.from_values(serializer.validated_data)
        return Response(self._present(self._service().customize(zone_code, profile)))

    def destroy(self, request, zone_code=None):
        self._get(zone_code)
        return Response(self._present(self._service().reset(zone_code)))

    def _get(self, zone_code):
        zone = self._service().get(zone_code)
        if zone is None:
            raise NotFound("Zone introuvable.")
        return zone

    @staticmethod
    def _present(zone):
        return ZoneComfortSerializer({"settings": zone}).data

    @staticmethod
    def _service():
        return ComfortProfileService.build()
