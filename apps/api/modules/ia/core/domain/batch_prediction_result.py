from dataclasses import dataclass

from .zone_prediction import ZonePrediction
from .zone_prediction_failure import ZonePredictionFailure


@dataclass(frozen=True)
class BatchPredictionResult:
    successes: tuple[ZonePrediction, ...]
    failures: tuple[ZonePredictionFailure, ...]
    skipped: tuple[str, ...] = ()
