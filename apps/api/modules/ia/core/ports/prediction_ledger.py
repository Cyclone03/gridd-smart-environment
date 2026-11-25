from datetime import datetime
from typing import Protocol

from modules.ia.core.domain.prediction_claim import PredictionClaim


class PredictionLedger(Protocol):
    """Registre durable des publications : une prédiction par (zone, instant
    d'entrée), rejouée à l'identique après un redémarrage."""

    def claim(self, zone_code: str, input_at: datetime) -> PredictionClaim | None:
        """``None`` si l'entrée est déjà publiée ou réservée par un autre cycle."""

    def store_pending(self, claim: PredictionClaim, *, generated_at, target_at, predicted_temperature_c,
                      predicted_humidity_percent, model_version, prediction_mode) -> None: ...

    def mark_published(self, claim: PredictionClaim) -> None: ...

    def release(self, claim: PredictionClaim) -> None: ...
