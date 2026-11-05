from rest_framework import serializers


class ComfortProfileSerializer(serializers.Serializer):
    """Plages de confort (lecture et écriture partielle)."""

    temperature_min = serializers.FloatField(min_value=-20, max_value=60)
    temperature_max = serializers.FloatField(min_value=-20, max_value=60)
    temperature_tolerance = serializers.FloatField(min_value=0.1, max_value=20)
    humidity_min = serializers.FloatField(min_value=0, max_value=100)
    humidity_max = serializers.FloatField(min_value=0, max_value=100)
    humidity_tolerance = serializers.FloatField(min_value=0.1, max_value=50)
