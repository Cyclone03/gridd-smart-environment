from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PendingPrediction:
    generated_at: datetime
    target_at: datetime
    predicted_temperature_c: float
    predicted_humidity_percent: float
    model_version: str
    prediction_mode: str
