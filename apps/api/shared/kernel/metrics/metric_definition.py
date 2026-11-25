from dataclasses import dataclass, field

from .operator import Operator


@dataclass(frozen=True)
class MetricDefinition:
    """Description d'un type de mesure suivi par GRIDD."""

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
    operators: tuple[str, ...] = field(default=Operator.ALL)
