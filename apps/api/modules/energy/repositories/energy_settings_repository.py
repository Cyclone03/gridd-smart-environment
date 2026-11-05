from modules.database.models import Zone
from modules.energy.domain.energy_profile import EnergyProfile
from modules.energy.domain.zone_energy_settings import ZoneEnergySettings


class EnergySettingsRepository:
    """Zones actives et leurs paramètres énergétiques enregistrés (lecture seule)."""

    def all(self) -> list[ZoneEnergySettings]:
        zones = Zone.objects.filter(active=True).select_related("energy_profile").order_by("name")
        return [self._settings(zone) for zone in zones]

    def get(self, zone_code) -> ZoneEnergySettings | None:
        zone = Zone.objects.filter(code=zone_code, active=True).select_related("energy_profile").first()
        return self._settings(zone) if zone else None

    @staticmethod
    def _settings(zone):
        stored = getattr(zone, "energy_profile", None)
        return ZoneEnergySettings(
            zone_code=zone.code,
            zone_name=zone.name,
            zone_type=zone.zone_type,
            stored=EnergyProfile.from_values({field: getattr(stored, field) for field in EnergyProfile.FIELDS})
            if stored
            else None,
        )
