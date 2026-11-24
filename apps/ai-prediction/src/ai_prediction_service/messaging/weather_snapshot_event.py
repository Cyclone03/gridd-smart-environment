import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from numbers import Real
from uuid import UUID, uuid4

from ..domain.weather import WeatherSnapshot

WEATHER_SNAPSHOT_EVENT_TYPE = "weather_snapshot.generated"
WEATHER_SNAPSHOT_EVENT_SOURCE = "ai_prediction_service"
WEATHER_PROVIDER = "open-meteo"


@dataclass(frozen=True)
class WeatherSnapshotEvent:
    event_id: str
    occurred_at: str
    generated_at: str
    provider: str
    current_at: str
    current_temperature_c: float
    current_relative_humidity_percent: float
    forecast_h1_at: str
    forecast_h1_temperature_c: float
    forecast_h1_relative_humidity_percent: float

    @classmethod
    def create(
        cls,
        *,
        snapshot: WeatherSnapshot,
        generated_at: datetime | None = None,
        event_id: str | None = None,
    ) -> "WeatherSnapshotEvent":
        generated = _as_utc(generated_at or datetime.now(timezone.utc), "generated_at")
        current_at = _as_utc(snapshot.current.timestamp_utc, "current_at")
        forecast_h1_at = _as_utc(snapshot.forecast_h1.timestamp_utc, "forecast_h1_at")
        if forecast_h1_at <= current_at:
            raise ValueError("forecast_h1_at must be later than current_at.")
        if forecast_h1_at <= generated:
            raise ValueError("forecast_h1_at must be later than generated_at.")

        if event_id is None:
            event_id = str(uuid4())
        else:
            try:
                event_id = str(UUID(event_id))
            except (AttributeError, TypeError, ValueError) as exc:
                raise ValueError("event_id must be a valid UUID.") from exc

        current_temperature = _finite_real(snapshot.current.temperature_c, "current_temperature_c")
        current_humidity = _humidity(
            snapshot.current.relative_humidity_pct,
            "current_relative_humidity_percent",
        )
        forecast_temperature = _finite_real(
            snapshot.forecast_h1.temperature_c,
            "forecast_h1_temperature_c",
        )
        forecast_humidity = _humidity(
            snapshot.forecast_h1.relative_humidity_pct,
            "forecast_h1_relative_humidity_percent",
        )

        return cls(
            event_id=event_id,
            occurred_at=generated.isoformat(),
            generated_at=generated.isoformat(),
            provider=WEATHER_PROVIDER,
            current_at=current_at.isoformat(),
            current_temperature_c=current_temperature,
            current_relative_humidity_percent=current_humidity,
            forecast_h1_at=forecast_h1_at.isoformat(),
            forecast_h1_temperature_c=forecast_temperature,
            forecast_h1_relative_humidity_percent=forecast_humidity,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "type": WEATHER_SNAPSHOT_EVENT_TYPE,
            "payload": {
                "generated_at": self.generated_at,
                "provider": self.provider,
                "current_at": self.current_at,
                "current_temperature_c": self.current_temperature_c,
                "current_relative_humidity_percent": self.current_relative_humidity_percent,
                "forecast_h1_at": self.forecast_h1_at,
                "forecast_h1_temperature_c": self.forecast_h1_temperature_c,
                "forecast_h1_relative_humidity_percent": self.forecast_h1_relative_humidity_percent,
            },
            "source": WEATHER_SNAPSHOT_EVENT_SOURCE,
            "event_id": self.event_id,
            "occurred_at": self.occurred_at,
            "correlation_id": None,
            "reply_to": None,
        }

    def encode(self) -> bytes:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")


def _as_utc(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware datetime.")
    return value.astimezone(timezone.utc)


def _finite_real(value: Real, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{label} must be a real number.")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{label} must be finite.")
    return converted


def _humidity(value: Real, label: str) -> float:
    converted = _finite_real(value, label)
    if not 0 <= converted <= 100:
        raise ValueError(f"{label} must be between 0 and 100 percent.")
    return converted
