from dataclasses import dataclass, field


@dataclass(frozen=True)
class QualityProfile:
    """Paramètres de contrôle de qualité d'une zone."""

    enabled: bool
    stuck_after_minutes: int
    # Variation maximale par minute, par type de mesure.
    rate_limits: dict = field(default_factory=dict)
