"""Catalogue central des types de mesures suivis par GRIDD.

Ce module est la seule source de vérité côté backend pour :

- les unités acceptées à l'ingestion (les capteurs envoient parfois « C » ou
  « celsius » pour la même grandeur) ;
- l'unité canonique exposée par l'API (historique, règles d'alarme) ;
- les limites physiques au-delà desquelles une mesure est jugée invalide ;
- la nature de la valeur (continue ou comptage entier) et les opérateurs de
  comparaison autorisés dans les règles d'alarme.

Ajouter un nouveau paramètre consiste à ajouter une entrée dans ``METRICS``
(et le choix correspondant dans ``Sensor.SensorType``).
"""

from dataclasses import dataclass, field


# Opérateurs de comparaison disponibles pour les règles d'alarme.
OPERATOR_GT = "gt"
OPERATOR_GTE = "gte"
OPERATOR_LT = "lt"
OPERATOR_LTE = "lte"
OPERATOR_OUTSIDE_RANGE = "outside_range"
OPERATOR_INSIDE_RANGE = "inside_range"

ALL_OPERATORS = (
    OPERATOR_GT,
    OPERATOR_GTE,
    OPERATOR_LT,
    OPERATOR_LTE,
    OPERATOR_OUTSIDE_RANGE,
    OPERATOR_INSIDE_RANGE,
)

RANGE_OPERATORS = frozenset({OPERATOR_OUTSIDE_RANGE, OPERATOR_INSIDE_RANGE})


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    label: str
    # Unité affichée et utilisée dans les règles d'alarme.
    unit: str
    # Unités acceptées à l'ingestion. ``None`` = aucune vérification.
    accepted_units: frozenset | None
    # Limites physiques (min, max). ``None`` = pas de contrôle.
    plausible_range: tuple[float, float] | None
    # Variation sous laquelle la tendance d'un historique est « stable ».
    trend_tolerance: float
    # Valeur de comptage : seuils et hystérésis doivent être entiers.
    integer: bool = False
    operators: tuple[str, ...] = field(default=ALL_OPERATORS)


METRICS: dict[str, MetricDefinition] = {
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
        # Aucun capteur CO₂ n'est déployé : on conserve le comportement
        # historique (pas de contrôle d'unité ni de plage).
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


def get_metric(key: str) -> MetricDefinition | None:
    return METRICS.get(key)


OPERATOR_LABELS = {
    OPERATOR_GT: "Supérieur à",
    OPERATOR_GTE: "Supérieur ou égal à",
    OPERATOR_LT: "Inférieur à",
    OPERATOR_LTE: "Inférieur ou égal à",
    OPERATOR_OUTSIDE_RANGE: "En dehors de l'intervalle",
    OPERATOR_INSIDE_RANGE: "À l'intérieur de l'intervalle",
}

OPERATOR_SYMBOLS = {
    OPERATOR_GT: ">",
    OPERATOR_GTE: "≥",
    OPERATOR_LT: "<",
    OPERATOR_LTE: "≤",
}
