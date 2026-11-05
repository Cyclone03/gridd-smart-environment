from modules.database.models import Zone

from .energy_profile import EnergyProfile


class EnergyDefaults:
    """Paramètres par défaut du modèle selon le type d'espace.

    Ordres de grandeur pour un bâtiment de bureaux ; à remplacer par les
    caractéristiques réelles de chaque espace dès qu'elles sont connues.
    Surface (m²), éclairage (W/m²), équipements fixes (W) et par personne (W),
    occupation supposée sans capteur.
    """

    BY_TYPE = {
        Zone.ZoneType.OFFICE: (20, 8, 150, 120, 1),
        Zone.ZoneType.MEETING_ROOM: (30, 10, 100, 60, 2),
        Zone.ZoneType.CUBICLE: (6, 8, 50, 120, 1),
        Zone.ZoneType.OPEN_WORKSPACE: (80, 8, 300, 120, 4),
        Zone.ZoneType.CLASSROOM: (60, 10, 300, 40, 10),
        Zone.ZoneType.SERVER_ROOM: (25, 5, 4000, 0, 0),
        Zone.ZoneType.LAB: (40, 10, 500, 150, 2),
    }
    OTHER = (20, 8, 100, 100, 0)

    # Déperditions de l'enveloppe par m² de plancher (W/K/m²).
    ENVELOPE_W_PER_K_PER_M2 = 1.0
    VENTILATION_L_S_PER_PERSON = 10
    OUTDOOR_TEMPERATURE_C = 5
    HEATING_COP = 2.5
    COOLING_COP = 3.0

    @classmethod
    def for_zone_type(cls, zone_type) -> EnergyProfile:
        area, lighting, base, per_person, occupancy = cls.BY_TYPE.get(zone_type, cls.OTHER)
        return EnergyProfile(
            floor_area_m2=area,
            lighting_w_per_m2=lighting,
            equipment_base_w=base,
            equipment_w_per_person=per_person,
            default_occupancy=occupancy,
            envelope_ua_w_per_k=area * cls.ENVELOPE_W_PER_K_PER_M2,
            ventilation_l_s_per_person=cls.VENTILATION_L_S_PER_PERSON,
            outdoor_temperature_c=cls.OUTDOOR_TEMPERATURE_C,
            heating_cop=cls.HEATING_COP,
            cooling_cop=cls.COOLING_COP,
        )
