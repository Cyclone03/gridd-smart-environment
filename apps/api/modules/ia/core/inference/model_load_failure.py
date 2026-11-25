from dataclasses import dataclass


@dataclass(frozen=True)
class ModelLoadFailure:
    zone_code: str
    error_type: str
    message: str
