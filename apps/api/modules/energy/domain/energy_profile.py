from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class EnergyProfile:
    """Paramètres du modèle d'estimation énergétique d'un espace."""

    floor_area_m2: float
    lighting_w_per_m2: float
    equipment_base_w: float
    equipment_w_per_person: float
    # Occupation supposée lorsqu'aucune mesure d'occupation n'est disponible.
    default_occupancy: int
    # Déperditions de l'enveloppe (W par degré d'écart intérieur/extérieur).
    envelope_ua_w_per_k: float
    ventilation_l_s_per_person: float
    outdoor_temperature_c: float
    heating_cop: float
    cooling_cop: float

    FIELDS = (
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

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_values(cls, values) -> "EnergyProfile":
        return cls(
            **{
                field: int(values[field]) if field == "default_occupancy" else float(values[field])
                for field in cls.FIELDS
            }
        )
