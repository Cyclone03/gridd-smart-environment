from dataclasses import dataclass
from datetime import datetime

from .pending_prediction import PendingPrediction


@dataclass(frozen=True)
class PredictionClaim:
    zone_code: str
    input_at: datetime
    event_id: str
    lease_token: str
    pending: PendingPrediction | None
