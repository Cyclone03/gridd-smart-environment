import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from numbers import Real
from uuid import UUID, uuid4

from ..models.zones import ZONE_MODEL_MAPPING

PREDICTION_EVENT_TYPE = "climate_prediction.generated"
PREDICTION_EVENT_SOURCE = "ai_prediction_service"
PREDICTION_MODES = frozenset({"experimental", "operational"})


@dataclass(frozen=True)
class ClimatePredictionEvent:
    event_id: str
    occurred_at: str
    zone_code: str
    generated_at: str
    target_at: str
    predicted_temperature_c: float
    predicted_humidity_percent: float
    model_version: str
    prediction_mode: str

    @classmethod
    def create(
        cls,
        *,
        zone_code: str,
        target_at: datetime,
        predicted_temperature_c: Real,
        predicted_humidity_percent: Real,
        model_version: str,
        prediction_mode: str,
        generated_at: datetime | None = None,
        event_id: str | None = None,
    ) -> "ClimatePredictionEvent":
        if zone_code not in ZONE_MODEL_MAPPING.values():
            raise ValueError(f"Unknown prediction zone code: {zone_code!r}.")

        generated = _as_utc(generated_at or datetime.now(timezone.utc), "generated_at")
        target = _as_utc(target_at, "target_at")
        if target <= generated:
            raise ValueError("target_at must be later than generated_at.")

        if not isinstance(model_version, str) or not model_version.strip():
            raise ValueError("model_version must not be empty.")
        if not isinstance(prediction_mode, str) or prediction_mode not in PREDICTION_MODES:
            raise ValueError(
                f"prediction_mode must be one of {sorted(PREDICTION_MODES)}."
            )

        if event_id is None:
            event_id = str(uuid4())
        else:
            try:
                event_id = str(UUID(event_id))
            except (AttributeError, TypeError, ValueError) as exc:
                raise ValueError("event_id must be a valid UUID.") from exc

        return cls(
            event_id=event_id,
            occurred_at=generated.isoformat(),
            zone_code=zone_code,
            generated_at=generated.isoformat(),
            target_at=target.isoformat(),
            predicted_temperature_c=_finite_real(
                predicted_temperature_c, "predicted_temperature_c"
            ),
            predicted_humidity_percent=_finite_real(
                predicted_humidity_percent, "predicted_humidity_percent"
            ),
            model_version=model_version.strip(),
            prediction_mode=prediction_mode,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "type": PREDICTION_EVENT_TYPE,
            "payload": {
                "zone_code": self.zone_code,
                "generated_at": self.generated_at,
                "target_at": self.target_at,
                "predicted_temperature_c": self.predicted_temperature_c,
                "predicted_humidity_percent": self.predicted_humidity_percent,
                "model_version": self.model_version,
                "prediction_mode": self.prediction_mode,
            },
            "source": PREDICTION_EVENT_SOURCE,
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
