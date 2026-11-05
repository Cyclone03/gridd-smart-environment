from django.utils.dateparse import parse_datetime

from modules.database.models import EnergyEstimate, EnergyProfile


class EnergyWriter:
    """Estimations énergétiques et paramètres personnalisés du modèle."""

    PROFILE_FIELDS = (
        "floor_area_m2",
        "lighting_w_per_m2",
        "equipment_base_w",
        "equipment_w_per_person",
        "default_occupancy",
        "envelope_ua_w_per_k",
        "ventilation_l_s_per_person",
        "outdoor_temperature_c",
        "heating_cop",
        "cooling_cop",
    )
    ENERGY_FIELDS = ("lighting_wh", "equipment_wh", "heating_wh", "cooling_wh", "total_wh")

    def record_estimate(self, zone, payload) -> tuple[EnergyEstimate, bool]:
        """Enregistre l'estimation, sauf si l'observation a déjà été intégrée."""
        observation_id = payload.get("observation_id")
        if observation_id is not None:
            existing = EnergyEstimate.objects.filter(observation_id=observation_id).first()
            if existing is not None:
                return existing, False
        estimate = EnergyEstimate.objects.create(
            zone=zone,
            observation_id=observation_id,
            start=parse_datetime(payload["start"]),
            end=parse_datetime(payload["end"]),
            duration_seconds=payload["duration_seconds"],
            indoor_temperature=payload.get("indoor_temperature"),
            occupancy=payload["occupancy"],
            occupancy_source=payload["occupancy_source"],
            hvac_estimated=payload["hvac_estimated"],
            **{field: payload[field] for field in self.ENERGY_FIELDS},
        )
        return estimate, True

    def save_profile(self, zone, values) -> EnergyProfile:
        profile, _ = EnergyProfile.objects.update_or_create(
            zone=zone,
            defaults={field: values[field] for field in self.PROFILE_FIELDS},
        )
        return profile

    def reset_profile(self, zone) -> int:
        deleted, _ = EnergyProfile.objects.filter(zone=zone).delete()
        return deleted
