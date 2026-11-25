from dataclasses import dataclass


@dataclass(frozen=True)
class SimulatedSensor:
    node_id: str
    metric: str
    unit: str
    zone_code: str
    zone_name: str
    last_value: float | None
