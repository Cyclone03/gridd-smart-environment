class PredictionMode:
    """Mode d'une prédiction climatique."""

    EXPERIMENTAL = "experimental"
    OPERATIONAL = "operational"

    VALUES = frozenset({EXPERIMENTAL, OPERATIONAL})
