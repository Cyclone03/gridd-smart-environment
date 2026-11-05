from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from modules.energy.domain.energy_profile import EnergyProfile
from modules.energy.serializers.energy_profile_serializer import EnergyProfileSerializer
from modules.energy.serializers.zone_energy_profile_serializer import ZoneEnergyProfileSerializer
from modules.energy.services.energy_profile_service import EnergyProfileService


class EnergyProfileController(viewsets.ViewSet):
    """``/api/energy/profiles/`` : paramètres du modèle par zone.

    ``PATCH`` personnalise une zone, ``DELETE`` rétablit les valeurs par défaut.
    """

    lookup_field = "zone_code"
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def list(self, request):
        return Response(ZoneEnergyProfileSerializer(self._service().list(), many=True).data)

    def retrieve(self, request, zone_code=None):
        return Response(ZoneEnergyProfileSerializer(self._get(zone_code)).data)

    def partial_update(self, request, zone_code=None):
        zone = self._get(zone_code)
        serializer = EnergyProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = EnergyProfile.from_values({**zone.profile.to_dict(), **serializer.validated_data})
        return Response(ZoneEnergyProfileSerializer(self._service().customize(zone_code, profile)).data)

    def destroy(self, request, zone_code=None):
        self._get(zone_code)
        return Response(ZoneEnergyProfileSerializer(self._service().reset(zone_code)).data)

    def _get(self, zone_code):
        zone = self._service().get(zone_code)
        if zone is None:
            raise NotFound("Zone introuvable.")
        return zone

    @staticmethod
    def _service():
        return EnergyProfileService.build()
