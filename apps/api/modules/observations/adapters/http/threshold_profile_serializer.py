from rest_framework import serializers

from modules.database.models import ThresholdProfile


class ThresholdProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThresholdProfile
        exclude = ["id", "zone"]
