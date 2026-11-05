from dataclasses import dataclass


@dataclass(frozen=True)
class QualityResult:
    status: str
    reason: str = ""
