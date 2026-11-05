from rest_framework import serializers


class AlertFilterSerializer(serializers.Serializer):
    """Paramètres de filtrage de ``GET /api/alerts/``."""

    MAX_LIMIT = 1000

    zone = serializers.CharField(required=False)
    active = serializers.CharField(required=False)
    rule = serializers.IntegerField(required=False, error_messages={"invalid": "Identifiant de règle invalide."})
    severity = serializers.CharField(required=False)
    since = serializers.DateTimeField(required=False, error_messages={"invalid": "Date et heure ISO 8601 attendue."})
    until = serializers.DateTimeField(required=False, error_messages={"invalid": "Date et heure ISO 8601 attendue."})
    limit = serializers.IntegerField(required=False, default=500, error_messages={"invalid": "Nombre entier attendu."})

    def validate_limit(self, value):
        return min(max(value, 1), self.MAX_LIMIT)
