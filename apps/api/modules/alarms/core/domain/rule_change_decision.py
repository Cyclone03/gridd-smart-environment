from dataclasses import dataclass


@dataclass(frozen=True)
class RuleChangeDecision:
    """Conséquence d'une modification de règle sur les alarmes en cours."""

    # Résolution à appliquer aux alertes en cours (et remise à zéro des états).
    resolution: str | None = None
    # Reporter la nouvelle gravité sur les alertes en cours.
    propagate_severity: bool = False
