from modules.database.models import ThresholdProfile
from modules.ingestion.domain.quality_profile import QualityProfile


class QualityProfileRepository:
    """Paramètres de contrôle de qualité d'une zone (lecture seule)."""

    def for_zone(self, zone_code) -> QualityProfile | None:
        profile = ThresholdProfile.objects.filter(zone__code=zone_code).first()
        if profile is None:
            return None
        return QualityProfile(
            enabled=profile.enabled,
            stuck_after_minutes=profile.stuck_after_minutes,
            rate_limits={
                "temperature": profile.max_temperature_delta_per_minute,
                "humidity": profile.max_humidity_delta_per_minute,
            },
        )
