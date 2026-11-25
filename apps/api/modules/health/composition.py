"""Racine de composition du module Health."""

from django.conf import settings
from django.utils import timezone

from modules.health.adapters.persistence.django_database_probe import DjangoDatabaseProbe
from modules.health.adapters.persistence.observation_freshness_repository import ObservationFreshnessRepository
from modules.health.core.services.health_service import HealthService


def health_service() -> HealthService:
    return HealthService(
        database=DjangoDatabaseProbe(),
        freshness=ObservationFreshnessRepository(),
        max_data_age_seconds=settings.HEALTH_MAX_DATA_AGE_SECONDS,
        components={
            "channel_layer": settings.CHANNEL_LAYERS["default"]["BACKEND"].rsplit(".", 1)[-1],
            "event_bus": settings.EVENT_BUS,
        },
        clock=timezone.now,
    )
