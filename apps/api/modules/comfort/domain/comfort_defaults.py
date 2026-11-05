from modules.database.models import Zone

from .comfort_profile import ComfortProfile


class ComfortDefaults:
    """Plages de confort par défaut selon le type d'espace.

    Espaces occupés : 20–24 °C et 30–60 % d'humidité relative, valeurs
    usuelles de confort en saison de chauffage (ordre de grandeur des
    recommandations ASHRAE 55 / ISO 7730, catégorie II). Salle serveur :
    plage recommandée pour les équipements (ASHRAE TC 9.9 : 18–27 °C).
    Ces valeurs sont des points de départ, modifiables par espace.
    """

    OCCUPIED = ComfortProfile(
        temperature_min=20,
        temperature_max=24,
        temperature_tolerance=2,
        humidity_min=30,
        humidity_max=60,
        humidity_tolerance=10,
    )
    SERVER_ROOM = ComfortProfile(
        temperature_min=18,
        temperature_max=27,
        temperature_tolerance=5,
        humidity_min=20,
        humidity_max=60,
        humidity_tolerance=20,
    )

    @classmethod
    def for_zone_type(cls, zone_type) -> ComfortProfile:
        return cls.SERVER_ROOM if zone_type == Zone.ZoneType.SERVER_ROOM else cls.OCCUPIED
