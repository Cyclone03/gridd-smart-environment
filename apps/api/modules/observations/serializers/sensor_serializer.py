from rest_framework import serializers

from modules.database.models import Sensor


class SensorSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True)

    class Meta:
        model = Sensor
        fields = "__all__"
