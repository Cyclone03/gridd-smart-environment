from rest_framework import serializers

from .energy_profile_serializer import EnergyProfileSerializer


class ZoneEnergyProfileSerializer(serializers.Serializer):
    """Zone et paramètres énergétiques applicables."""

    zone_code = serializers.CharField()
    zone_name = serializers.CharField()
    zone_type = serializers.CharField()
    customized = serializers.BooleanField()
    profile = EnergyProfileSerializer()
