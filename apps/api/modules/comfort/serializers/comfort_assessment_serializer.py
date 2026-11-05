from rest_framework import serializers


class ComfortAssessmentSerializer(serializers.Serializer):
    assessed_at = serializers.DateTimeField()
    temperature = serializers.FloatField(allow_null=True)
    humidity = serializers.FloatField(allow_null=True)
    temperature_status = serializers.CharField()
    humidity_status = serializers.CharField()
    level = serializers.CharField()
    score = serializers.FloatField(allow_null=True)
