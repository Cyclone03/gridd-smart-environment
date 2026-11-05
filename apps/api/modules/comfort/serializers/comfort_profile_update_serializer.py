from rest_framework import serializers

from modules.comfort.domain.comfort_profile_validator import ComfortProfileValidator

from .comfort_profile_serializer import ComfortProfileSerializer


class ComfortProfileUpdateSerializer(ComfortProfileSerializer):
    """Modification partielle : les champs fournis complètent les plages actuelles
    (``context["current"]``), puis l'ensemble est contrôlé."""

    validator = ComfortProfileValidator()

    def validate(self, attrs):
        values = {**self.context["current"].to_dict(), **attrs}
        errors = self.validator.errors(values)
        if errors:
            raise serializers.ValidationError(errors)
        return values
