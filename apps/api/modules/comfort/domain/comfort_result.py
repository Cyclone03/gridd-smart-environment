from dataclasses import dataclass


@dataclass(frozen=True)
class ComfortResult:
    """Résultat de l'évaluation du confort d'un espace."""

    temperature: float | None
    humidity: float | None
    temperature_status: str
    humidity_status: str
    level: str
    # 0 à 100 ; ``None`` si aucune mesure n'est disponible.
    score: float | None
