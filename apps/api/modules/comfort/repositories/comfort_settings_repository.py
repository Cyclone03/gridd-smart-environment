from modules.comfort.domain.comfort_profile import ComfortProfile
from modules.comfort.domain.zone_comfort_settings import ZoneComfortSettings
from modules.database.models import Zone


class ComfortSettingsRepository:
    """Zones actives et leurs plages de confort enregistrées (lecture seule)."""

    def all(self) -> list[ZoneComfortSettings]:
        zones = Zone.objects.filter(active=True).select_related("comfort_profile").order_by("name")
        return [self._settings(zone) for zone in zones]

    def get(self, zone_code) -> ZoneComfortSettings | None:
        zone = Zone.objects.filter(code=zone_code, active=True).select_related("comfort_profile").first()
        return self._settings(zone) if zone else None

    @staticmethod
    def _settings(zone):
        stored = getattr(zone, "comfort_profile", None)
        return ZoneComfortSettings(
            zone_code=zone.code,
            zone_name=zone.name,
            zone_type=zone.zone_type,
            stored=ComfortProfile.from_values({field: getattr(stored, field) for field in ComfortProfile.FIELDS})
            if stored
            else None,
        )
