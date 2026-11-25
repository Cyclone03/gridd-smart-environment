from dataclasses import dataclass
from datetime import datetime

from .publication_receipt import PublicationReceipt


@dataclass(frozen=True)
class ZonePrediction:
    zone_code: str
    input_at: datetime
    target_at: datetime
    predicted_temperature_c: float
    predicted_humidity_percent: float
    model_version: str
    prediction_mode: str
    receipt: PublicationReceipt
