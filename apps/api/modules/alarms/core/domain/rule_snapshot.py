from dataclasses import dataclass


@dataclass(frozen=True)
class RuleSnapshot:
    """Règle d'alarme telle qu'utilisée par le moteur d'évaluation."""

    id: int
    name: str
    metric: str
    operator: str
    threshold: float
    threshold_high: float | None
    severity: str
    min_duration_seconds: int
    hysteresis: float
