from dataclasses import dataclass


@dataclass(frozen=True)
class ZonePredictionFailure:
    zone_code: str
    error_type: str
    message: str
