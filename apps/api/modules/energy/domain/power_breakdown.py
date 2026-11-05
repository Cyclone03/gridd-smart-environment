from dataclasses import dataclass


@dataclass(frozen=True)
class PowerBreakdown:
    """Puissance électrique estimée d'un espace, par usage (W)."""

    lighting_w: float
    equipment_w: float
    heating_w: float
    cooling_w: float
    # Faux si la température intérieure est inconnue (chauffage et climatisation non estimés).
    hvac_estimated: bool

    @property
    def total_w(self) -> float:
        return self.lighting_w + self.equipment_w + self.heating_w + self.cooling_w

    def energy_wh(self, seconds) -> dict:
        hours = seconds / 3600
        return {
            "lighting_wh": round(self.lighting_w * hours, 3),
            "equipment_wh": round(self.equipment_w * hours, 3),
            "heating_wh": round(self.heating_w * hours, 3),
            "cooling_wh": round(self.cooling_w * hours, 3),
            "total_wh": round(self.total_w * hours, 3),
        }
