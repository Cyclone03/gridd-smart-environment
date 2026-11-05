from rest_framework import serializers

from .comfort_assessment_serializer import ComfortAssessmentSerializer
from .comfort_profile_serializer import ComfortProfileSerializer


class ZoneComfortSerializer(serializers.Serializer):
    """Zone, plages de confort applicables et (facultatif) dernière évaluation."""

    zone_code = serializers.CharField(source="settings.zone_code")
    zone_name = serializers.CharField(source="settings.zone_name")
    zone_type = serializers.CharField(source="settings.zone_type")
    customized = serializers.BooleanField(source="settings.customized")
    profile = ComfortProfileSerializer(source="settings.profile")
    assessment = ComfortAssessmentSerializer(allow_null=True, default=None)
