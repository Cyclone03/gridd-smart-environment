import logging
import math
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from numbers import Real

from modules.ia.core.domain.batch_prediction_result import BatchPredictionResult
from modules.ia.core.domain.climate_prediction_event import ClimatePredictionEvent
from modules.ia.core.domain.collection_snapshot import CollectionSnapshot
from modules.ia.core.domain.metric_observation import MetricObservation
from modules.ia.core.domain.publication_receipt import PublicationReceipt
from modules.ia.core.domain.weather_snapshot import WeatherSnapshot
from modules.ia.core.domain.weather_snapshot_event import WeatherSnapshotEvent
from modules.ia.core.domain.zone_prediction import ZonePrediction
from modules.ia.core.domain.zone_prediction_failure import ZonePredictionFailure
from modules.ia.core.domain.zones import ZONE_MODEL_MAPPING
from modules.ia.core.errors import CollectionError, PredictionInputError
from modules.ia.core.inference.contract import INPUT_FEATURES
from modules.ia.core.ports.prediction_ledger import PredictionLedger
from modules.ia.core.ports.prediction_publisher import PredictionPublisher

from .data_collection_service import DataCollectionService

logger = logging.getLogger(__name__)

MAX_DATA_AGE = timedelta(minutes=10)
MAX_INPUT_SKEW = timedelta(minutes=5)
MAX_FUTURE_CLOCK_SKEW = timedelta(minutes=1)
MAX_OBSERVED_AFTER_RECEIVED_SKEW = timedelta(seconds=1)
TEMPERATURE_UNITS = frozenset({"C", "°C"})
HUMIDITY_UNITS = frozenset({"%"})


class PredictionOrchestrator:
    """Collects, validates, predicts, and publishes one zone at a time.

    Ports : ``PredictionPublisher`` (``producer``) and ``PredictionLedger``
    (``ledger``, optional). ``predictor`` is a ``ModelPredictor`` and
    ``registry`` an ``ArtifactRegistry``.
    """

    def __init__(
        self,
        *,
        collection: DataCollectionService,
        predictor,
        registry,
        producer: PredictionPublisher,
        ledger: PredictionLedger | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self._collection = collection
        self._predictor = predictor
        self._registry = registry
        self._producer = producer
        self._ledger = ledger
        self._now = now

    def run_zone(self, zone_code: str) -> ZonePrediction | None:
        if zone_code not in self._registry.zone_codes():
            raise ValueError(f"No registered model artifacts for zone {zone_code!r}.")

        weather = self._collection.fetch_weather()
        self._publish_weather(weather)
        snapshot = self._collection.collect_with_weather((zone_code,), weather)
        return self._predict_from_snapshot(zone_code, snapshot)

    def _predict_from_snapshot(
        self,
        zone_code: str,
        snapshot: CollectionSnapshot,
    ) -> ZonePrediction | None:
        input_at = self._validate_snapshot(snapshot, zone_code, self._utc_now())
        target_at = input_at + timedelta(hours=1)
        if target_at <= self._utc_now():
            raise PredictionInputError("The H+1 target is no longer in the future; input data are too old.")

        spec = self._registry.for_zone(zone_code)
        model_version = f"modelZone{spec.zone_number}:sha256:{spec.model.sha256}"
        prediction_mode = "experimental"
        claim = self._ledger.claim(zone_code, input_at) if self._ledger is not None else None
        if self._ledger is not None and claim is None:
            logger.info("Skipping duplicate or already-claimed input: zone=%s input_at=%s", zone_code, input_at)
            return None

        try:
            if claim is not None and claim.pending is not None:
                pending = claim.pending
                if pending.target_at != target_at:
                    raise PredictionInputError("Pending prediction target does not match the current input time.")
                temperature = pending.predicted_temperature_c
                humidity = pending.predicted_humidity_percent
                model_version = pending.model_version
                prediction_mode = pending.prediction_mode
                generated_at = pending.generated_at
                target_at = pending.target_at
            else:
                features = self._collection.build_model_features(
                    snapshot,
                    zone_code,
                    weather_point=snapshot.weather.current,
                )
                if tuple(features) != INPUT_FEATURES:
                    raise PredictionInputError("Collected features do not match the confirmed X order.")

                temperature, humidity = self._predictor.predict_one(zone_code, features)
                temperature = _finite_prediction(temperature, "temperature")
                humidity = _finite_prediction(humidity, "humidity")
                if not 0 <= humidity <= 100:
                    raise PredictionInputError("Predicted humidity must be between 0 and 100 percent.")
                generated_at = self._utc_now()
                if target_at <= generated_at:
                    raise PredictionInputError("The H+1 target passed before inference completed.")
                if claim is not None:
                    ClimatePredictionEvent.create(
                        zone_code=zone_code,
                        target_at=target_at,
                        predicted_temperature_c=temperature,
                        predicted_humidity_percent=humidity,
                        model_version=model_version,
                        prediction_mode=prediction_mode,
                        generated_at=generated_at,
                        event_id=claim.event_id,
                    )
                    self._ledger.store_pending(
                        claim,
                        generated_at=generated_at,
                        target_at=target_at,
                        predicted_temperature_c=temperature,
                        predicted_humidity_percent=humidity,
                        model_version=model_version,
                        prediction_mode=prediction_mode,
                    )

            event = ClimatePredictionEvent.create(
                zone_code=zone_code,
                target_at=target_at,
                predicted_temperature_c=temperature,
                predicted_humidity_percent=humidity,
                model_version=model_version,
                prediction_mode=prediction_mode,
                generated_at=generated_at,
                event_id=claim.event_id if claim is not None else None,
            )
            receipt = self._producer.publish_prediction(event)
            if claim is not None:
                self._ledger.mark_published(claim)
            return ZonePrediction(
                zone_code=zone_code,
                input_at=input_at,
                target_at=target_at,
                predicted_temperature_c=temperature,
                predicted_humidity_percent=humidity,
                model_version=model_version,
                prediction_mode=prediction_mode,
                receipt=receipt,
            )
        except Exception:
            if claim is not None:
                try:
                    self._ledger.release(claim)
                except Exception:
                    logger.exception("Could not release prediction ledger claim for zone %s.", zone_code)
            raise

    def run_all(self) -> BatchPredictionResult:
        successes = []
        failures = []
        skipped = []
        zone_codes = tuple(ZONE_MODEL_MAPPING.values())
        try:
            weather = self._collection.fetch_weather()
            self._publish_weather(weather)
        except Exception as exc:
            logger.exception("Could not collect or publish the shared weather snapshot.")
            failures.extend(
                ZonePredictionFailure(
                    zone_code=zone_code,
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
                for zone_code in zone_codes
            )
            return BatchPredictionResult(tuple(successes), tuple(failures), tuple(skipped))

        for zone_code in zone_codes:
            try:
                snapshot = self._collection.collect_with_weather((zone_code,), weather)
                prediction = self._predict_from_snapshot(zone_code, snapshot)
                if prediction is None:
                    skipped.append(zone_code)
                else:
                    successes.append(prediction)
            except Exception as exc:
                # This boundary deliberately isolates one zone; every failure is logged and returned.
                if isinstance(exc, (PredictionInputError, CollectionError)):
                    # Expected data condition (stale, missing, incoherent…): no stack trace.
                    logger.error("Climate prediction skipped for zone %s: %s", zone_code, exc)
                else:
                    logger.exception("Climate prediction failed for zone %s.", zone_code)
                failures.append(
                    ZonePredictionFailure(
                        zone_code=zone_code,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
        return BatchPredictionResult(tuple(successes), tuple(failures), tuple(skipped))

    def _publish_weather(self, weather: WeatherSnapshot) -> PublicationReceipt:
        return self._producer.publish_weather_snapshot(
            WeatherSnapshotEvent.create(snapshot=weather, generated_at=self._utc_now())
        )

    def _utc_now(self) -> datetime:
        return _utc_datetime(self._now(), "current time")

    def _validate_snapshot(self, snapshot: CollectionSnapshot, zone_code: str, now: datetime) -> datetime:
        zone = snapshot.zones.get(zone_code)
        if zone is None:
            raise PredictionInputError(f"No indoor observations were collected for zone {zone_code!r}.")
        if zone.zone_code != zone_code:
            raise PredictionInputError(f"Observation zone code does not match {zone_code!r}.")

        temperature = zone.temperature
        humidity = zone.humidity
        _validate_observation(temperature, "temperature", TEMPERATURE_UNITS)
        _validate_observation(humidity, "humidity", HUMIDITY_UNITS)
        if temperature.quality_status != "normal" or humidity.quality_status != "normal":
            raise PredictionInputError("Only observations with quality_status='normal' may be used.")
        if not 0 <= humidity.value <= 100:
            raise PredictionInputError("Indoor humidity must be between 0 and 100 percent.")

        temperature_at = _observation_time(temperature, "temperature")
        humidity_at = _observation_time(humidity, "humidity")
        weather_at = _utc_datetime(snapshot.weather.current.timestamp_utc, "Open-Meteo current time")
        received_at = _utc_datetime(temperature.received_at, "temperature received_at")
        humidity_received_at = _utc_datetime(humidity.received_at, "humidity received_at")
        if (
            temperature_at - received_at > MAX_OBSERVED_AFTER_RECEIVED_SKEW
            or humidity_at - humidity_received_at > MAX_OBSERVED_AFTER_RECEIVED_SKEW
        ):
            raise PredictionInputError(
                "An observation timestamp is more than one second ahead of its receipt timestamp."
            )

        timestamps = (temperature_at, humidity_at, weather_at)
        for label, timestamp in (
            ("temperature observation", temperature_at),
            ("humidity observation", humidity_at),
            ("Open-Meteo current conditions", weather_at),
        ):
            age = now - timestamp
            if age > MAX_DATA_AGE:
                raise PredictionInputError(f"{label} are stale ({age.total_seconds():.0f} seconds old).")
            if age < -MAX_FUTURE_CLOCK_SKEW:
                raise PredictionInputError(f"{label} have a timestamp in the future.")

        if max(timestamps) - min(timestamps) > MAX_INPUT_SKEW:
            raise PredictionInputError(
                "Indoor and outdoor timestamps differ by more than five minutes "
                f"(temperature={temperature_at.isoformat()}, humidity={humidity_at.isoformat()}, "
                f"Open-Meteo current={weather_at.isoformat()})."
            )

        # Anchor H+1 to the newest timestamp among the coherent input values.
        return max(timestamps)


def _validate_observation(
    observation: MetricObservation,
    label: str,
    allowed_units: frozenset[str],
) -> None:
    if observation.unit not in allowed_units:
        raise PredictionInputError(
            f"{label} unit {observation.unit!r} is incompatible; expected one of {sorted(allowed_units)}."
        )
    if isinstance(observation.value, bool) or not isinstance(observation.value, Real):
        raise PredictionInputError(f"{label} observation must be numeric.")
    if not math.isfinite(float(observation.value)):
        raise PredictionInputError(f"{label} observation must be finite.")


def _observation_time(observation: MetricObservation, label: str) -> datetime:
    if observation.observed_at is None:
        raise PredictionInputError(f"{label} observation is missing observed_at; received_at is not a substitute.")
    return _utc_datetime(observation.observed_at, f"{label} observed_at")


def _utc_datetime(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PredictionInputError(f"{label} must be a timezone-aware timestamp.")
    return value.astimezone(timezone.utc)


def _finite_prediction(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise PredictionInputError(f"Predicted {label} must be a finite number.")
    return float(value)
