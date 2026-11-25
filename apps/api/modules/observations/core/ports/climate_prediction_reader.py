from typing import Protocol


class ClimatePredictionReader(Protocol):
    """Dernière prédiction climatique de chaque zone active."""

    def latest_by_zone(self): ...
