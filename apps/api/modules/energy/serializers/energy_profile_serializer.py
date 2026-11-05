from rest_framework import serializers


class EnergyProfileSerializer(serializers.Serializer):
    """Paramètres du modèle énergétique (lecture et écriture partielle)."""

    floor_area_m2 = serializers.FloatField(min_value=0, max_value=10_000)
    lighting_w_per_m2 = serializers.FloatField(min_value=0, max_value=50)
    equipment_base_w = serializers.FloatField(min_value=0, max_value=1_000_000)
    equipment_w_per_person = serializers.FloatField(min_value=0, max_value=5_000)
    default_occupancy = serializers.IntegerField(min_value=0, max_value=500)
    envelope_ua_w_per_k = serializers.FloatField(min_value=0, max_value=100_000)
    ventilation_l_s_per_person = serializers.FloatField(min_value=0, max_value=100)
    outdoor_temperature_c = serializers.FloatField(min_value=-50, max_value=50)
    heating_cop = serializers.FloatField(min_value=0.5, max_value=10)
    cooling_cop = serializers.FloatField(min_value=0.5, max_value=10)
