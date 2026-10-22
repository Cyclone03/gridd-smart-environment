from rest_framework import serializers
from .models import Zone, Sensor, Observation, ThresholdProfile, Alert


class ThresholdProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThresholdProfile
        exclude = ["id", "zone"]


class ZoneSerializer(serializers.ModelSerializer):
    threshold_profile = ThresholdProfileSerializer(read_only=True)

    class Meta:
        model = Zone
        fields = ["id", "name", "code", "zone_type", "description", "active", "threshold_profile"]


class SensorSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True)

    class Meta:
        model = Sensor
        fields = "__all__"


class ObservationSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    sensor_node_id = serializers.CharField(source="sensor.node_id", read_only=True)

    class Meta:
        model = Observation
        fields = "__all__"


class AlertSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True)

    class Meta:
        model = Alert
        fields = "__all__"
