from dataclasses import dataclass

from .metric_observation import MetricObservation


@dataclass(frozen=True)
class ZoneObservations:
    zone_code: str
    temperature: MetricObservation
    humidity: MetricObservation
