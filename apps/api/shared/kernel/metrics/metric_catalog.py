from .metric_definition import MetricDefinition


class MetricCatalog:
    """Catalogue central des types de mesures (noyau partagé).

    Seule source de vérité pour :

    - les unités acceptées à l'ingestion (les capteurs envoient parfois « C »
      ou « celsius » pour la même grandeur) ;
    - l'unité canonique exposée par l'API (historique, règles d'alarme) ;
    - les limites physiques au-delà desquelles une mesure est invalide ;
    - la nature de la valeur (continue ou comptage) et les opérateurs
      autorisés dans les règles d'alarme.

    Ajouter un paramètre : une entrée ici, le choix correspondant dans
    ``Sensor.SensorType`` et son topic capteur dans la configuration.
    """

    _DEFINITIONS = {
        "temperature": MetricDefinition(
            key="temperature",
            label="Température",
            unit="°C",
            accepted_units=frozenset({"°C", "C", "celsius"}),
            plausible_range=(-20, 60),
            trend_tolerance=0.2,
        ),
        "humidity": MetricDefinition(
            key="humidity",
            label="Humidité",
            unit="%",
            accepted_units=frozenset({"%", "percent"}),
            plausible_range=(0, 100),
            trend_tolerance=1,
        ),
        "co2": MetricDefinition(
            key="co2",
            label="CO₂",
            unit="ppm",
            # Aucun capteur CO₂ n'est déployé : pas de contrôle d'unité ni de plage.
            accepted_units=None,
            plausible_range=None,
            trend_tolerance=20,
        ),
        "sound_level": MetricDefinition(
            key="sound_level",
            label="Niveau sonore",
            unit="dBA",
            accepted_units=frozenset({"dBA", "dbA", "dba"}),
            plausible_range=(0, 150),
            trend_tolerance=1,
        ),
        "occupancy": MetricDefinition(
            key="occupancy",
            label="Occupation",
            unit="personnes",
            accepted_units=frozenset({"count", "person", "persons", "people"}),
            plausible_range=(0, 500),
            trend_tolerance=1,
            integer=True,
        ),
    }

    @classmethod
    def get(cls, key) -> MetricDefinition | None:
        return cls._DEFINITIONS.get(key)

    @classmethod
    def keys(cls) -> tuple[str, ...]:
        return tuple(cls._DEFINITIONS)

    @classmethod
    def definitions(cls) -> tuple[MetricDefinition, ...]:
        return tuple(cls._DEFINITIONS.values())

    @classmethod
    def position(cls, key) -> int:
        """Rang d'affichage d'une mesure (ordre du catalogue)."""
        keys = cls.keys()
        return keys.index(key) if key in keys else len(keys)
