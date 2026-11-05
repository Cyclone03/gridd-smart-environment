from dataclasses import dataclass

from .energy_defaults import EnergyDefaults
from .energy_profile import EnergyProfile


@dataclass(frozen=True)
class ZoneEnergySettings:
    """Paramètres énergétiques applicables à une zone : personnalisés ou par défaut."""

    zone_code: str
    zone_name: str
    zone_type: str
    stored: EnergyProfile | None

    @property
    def customized(self) -> bool:
        return self.stored is not None

    @property
    def profile(self) -> EnergyProfile:
        return self.stored or EnergyDefaults.for_zone_type(self.zone_type)
