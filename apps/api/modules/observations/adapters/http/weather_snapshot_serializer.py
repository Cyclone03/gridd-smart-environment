from rest_framework import serializers

from modules.database.models import WeatherSnapshot


class WeatherSnapshotSerializer(serializers.ModelSerializer):
    weather_snapshot_id = serializers.IntegerField(source="id", read_only=True)
    weather_snapshot_event_id = serializers.UUIDField(source="event_id", read_only=True)

    class Meta:
        model = WeatherSnapshot
        fields = [
            "weather_snapshot_id",
            "weather_snapshot_event_id",
            "generated_at",
            "provider",
            "current_at",
            "current_temperature_c",
            "current_relative_humidity_percent",
            "forecast_h1_at",
            "forecast_h1_temperature_c",
            "forecast_h1_relative_humidity_percent",
        ]
