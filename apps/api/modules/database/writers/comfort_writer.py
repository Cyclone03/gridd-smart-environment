from django.utils.dateparse import parse_datetime

from modules.database.models import ComfortAssessment, ComfortProfile


class ComfortWriter:
    """Évaluations de confort et plages de confort personnalisées."""

    PROFILE_FIELDS = (
        "temperature_min",
        "temperature_max",
        "temperature_tolerance",
        "humidity_min",
        "humidity_max",
        "humidity_tolerance",
    )

    def record_assessment(self, zone, payload) -> tuple[ComfortAssessment, bool]:
        """Enregistre l'évaluation, sauf si l'observation a déjà été évaluée."""
        observation_id = payload.get("observation_id")
        if observation_id is not None:
            existing = ComfortAssessment.objects.filter(observation_id=observation_id).first()
            if existing is not None:
                return existing, False
        assessment = ComfortAssessment.objects.create(
            zone=zone,
            observation_id=observation_id,
            assessed_at=parse_datetime(payload["assessed_at"]),
            temperature=payload.get("temperature"),
            humidity=payload.get("humidity"),
            temperature_status=payload["temperature_status"],
            humidity_status=payload["humidity_status"],
            level=payload["level"],
            score=payload.get("score"),
        )
        return assessment, True

    def save_profile(self, zone, values) -> ComfortProfile:
        profile, _ = ComfortProfile.objects.update_or_create(
            zone=zone,
            defaults={field: values[field] for field in self.PROFILE_FIELDS},
        )
        return profile

    def reset_profile(self, zone) -> int:
        deleted, _ = ComfortProfile.objects.filter(zone=zone).delete()
        return deleted
