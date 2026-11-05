from dataclasses import dataclass

from .comfort_defaults import ComfortDefaults
from .comfort_profile import ComfortProfile


@dataclass(frozen=True)
class ZoneComfortSettings:
    """Plages de confort applicables à une zone : personnalisées ou par défaut."""

    zone_code: str
    zone_name: str
    zone_type: str
    stored: ComfortProfile | None

    @property
    def customized(self) -> bool:
        return self.stored is not None

    @property
    def profile(self) -> ComfortProfile:
        return self.stored or ComfortDefaults.for_zone_type(self.zone_type)
