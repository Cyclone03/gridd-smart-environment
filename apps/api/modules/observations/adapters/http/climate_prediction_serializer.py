from rest_framework import serializers

from modules.database.models import ClimatePrediction


class ClimatePredictionSerializer(serializers.ModelSerializer):
    prediction_id = serializers.IntegerField(source="id", read_only=True)
    prediction_event_id = serializers.UUIDField(source="event_id", read_only=True)
    zone_code = serializers.CharField(source="zone.code", read_only=True)

    class Meta:
        model = ClimatePrediction
        fields = [
            "prediction_id",
            "prediction_event_id",
            "zone_code",
            "generated_at",
            "target_at",
            "predicted_temperature_c",
            "predicted_humidity_percent",
            "model_version",
            "prediction_mode",
        ]
