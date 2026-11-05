from rest_framework import serializers

from modules.database.models import Observation


class ObservationSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    sensor_node_id = serializers.CharField(source="sensor.node_id", read_only=True)

    class Meta:
        model = Observation
        exclude = ["event_id"]
