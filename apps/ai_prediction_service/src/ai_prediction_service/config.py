import math
import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ServiceSettings:
    gridd_api_base_url: str
    open_meteo_latitude: float
    open_meteo_longitude: float
    http_timeout_seconds: float = 10.0

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None):
        values = os.environ if environ is None else environ
        base_url = values.get("GRIDD_API_BASE_URL", "http://localhost:8000").rstrip("/")
        if not base_url:
            raise ValueError("GRIDD_API_BASE_URL must not be empty.")

        latitude = _required_float(values, "OPEN_METEO_LATITUDE")
        longitude = _required_float(values, "OPEN_METEO_LONGITUDE")
        timeout = _optional_float(values, "HTTP_TIMEOUT_SECONDS", 10.0)
        if not -90 <= latitude <= 90:
            raise ValueError("OPEN_METEO_LATITUDE must be between -90 and 90.")
        if not -180 <= longitude <= 180:
            raise ValueError("OPEN_METEO_LONGITUDE must be between -180 and 180.")
        if timeout <= 0:
            raise ValueError("HTTP_TIMEOUT_SECONDS must be greater than zero.")

        return cls(
            gridd_api_base_url=base_url,
            open_meteo_latitude=latitude,
            open_meteo_longitude=longitude,
            http_timeout_seconds=timeout,
        )


def _required_float(values: Mapping[str, str], name: str) -> float:
    if name not in values:
        raise ValueError(f"{name} is required.")
    return _parse_float(values[name], name)


def _optional_float(values: Mapping[str, str], name: str, default: float) -> float:
    if name not in values:
        return default
    return _parse_float(values[name], name)


def _parse_float(value: str, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number.") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite.")
    return parsed
