from rest_framework import serializers

from modules.database.models import Zone
from shared.metrics.metric_catalog import MetricCatalog

from .threshold_profile_serializer import ThresholdProfileSerializer


class ZoneSerializer(serializers.ModelSerializer):
    threshold_profile = ThresholdProfileSerializer(read_only=True)
    # Types de mesure réellement disponibles (capteurs actifs).
    metrics = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = ["id", "name", "code", "zone_type", "description", "active", "metrics", "threshold_profile"]

    def get_metrics(self, zone):
        sensors = getattr(zone, "active_sensors", None)
        if sensors is None:
            sensors = zone.sensors.filter(active=True)
        return sorted({sensor.sensor_type for sensor in sensors}, key=MetricCatalog.position)
