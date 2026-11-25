import math
from typing import Callable, Sequence

from modules.ia.core.domain.metric_observation import MetricObservation
from modules.ia.core.domain.timestamps import parse_utc_timestamp
from modules.ia.core.domain.zone_observations import ZoneObservations
from modules.ia.core.errors import (
    GriddApiError,
    HttpRequestError,
    IncompleteObservationsError,
    InvalidGriddResponse,
    TimestampFormatError,
    UnknownZoneError,
)

from .http_json import fetch_json

JsonTransport = Callable[..., object]
REQUIRED_METRICS = ("temperature", "humidity")


class GriddApiObservationSource:
    """Adaptateur HTTP du port ``ObservationSource`` : lit l'API REST GRIDD
    (``/api/zones/`` et ``/api/observations/latest/``). Utile quand le module
    IA est déployé sans accès à la base de données.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 10.0,
        transport: JsonTransport = fetch_json,
    ):
        base_url = base_url.rstrip("/")
        if not base_url:
            raise ValueError("base_url must not be empty.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def fetch_latest(self, zone_codes: Sequence[str] | None = None) -> dict[str, ZoneObservations]:
        zones_payload = self._get_json("/api/zones/")
        if not isinstance(zones_payload, list):
            raise InvalidGriddResponse("The zones endpoint must return a JSON array.")

        active_codes = []
        for index, zone in enumerate(zones_payload):
            if not isinstance(zone, dict) or not isinstance(zone.get("code"), str) or not zone["code"]:
                raise InvalidGriddResponse(f"Zone entry {index} has no valid code.")
            if zone["code"] in active_codes:
                raise InvalidGriddResponse(f"Duplicate active zone code: {zone['code']}.")
            active_codes.append(zone["code"])
        if not active_codes:
            raise IncompleteObservationsError("The zones endpoint returned no active zones.")

        requested_codes = active_codes if zone_codes is None else _validate_requested_codes(zone_codes)
        unknown_codes = [code for code in requested_codes if code not in active_codes]
        if unknown_codes:
            raise UnknownZoneError(f"Unknown or inactive zone code(s): {', '.join(unknown_codes)}.")

        observations_payload = self._get_json("/api/observations/latest/")
        if not isinstance(observations_payload, list):
            raise InvalidGriddResponse("The latest observations endpoint must return a JSON array.")

        selected_codes = set(requested_codes)
        latest: dict[str, dict[str, MetricObservation]] = {code: {} for code in requested_codes}
        active_code_set = set(active_codes)
        for index, item in enumerate(observations_payload):
            if not isinstance(item, dict):
                raise InvalidGriddResponse(f"Observation entry {index} must be a JSON object.")
            code = item.get("zone_code")
            if not isinstance(code, str) or code not in active_code_set:
                raise InvalidGriddResponse(f"Observation entry {index} references an unknown zone code.")
            metric = item.get("type")
            if metric not in REQUIRED_METRICS or code not in selected_codes:
                continue
            if metric in latest[code]:
                raise InvalidGriddResponse(f"Duplicate latest {metric} observation for zone {code}.")
            latest[code][metric] = _parse_observation(item, index)

        result = {}
        for code in requested_codes:
            metrics = latest[code]
            missing = [metric for metric in REQUIRED_METRICS if metric not in metrics]
            if missing:
                raise IncompleteObservationsError(
                    f"Zone {code} is missing latest observation(s): {', '.join(missing)}."
                )
            result[code] = ZoneObservations(
                zone_code=code,
                temperature=metrics["temperature"],
                humidity=metrics["humidity"],
            )
        return result

    def _get_json(self, path: str) -> object:
        try:
            return self._transport(f"{self._base_url}{path}", timeout=self._timeout_seconds)
        except HttpRequestError as exc:
            raise GriddApiError(f"GRIDD API request failed for {path}.") from exc


def _validate_requested_codes(zone_codes: Sequence[str]) -> list[str]:
    if isinstance(zone_codes, str):
        raise ValueError("zone_codes must be a sequence of codes, not a string.")
    codes = list(zone_codes)
    if not codes:
        raise ValueError("zone_codes must contain at least one zone code.")
    if any(not isinstance(code, str) or not code for code in codes):
        raise ValueError("zone_codes must contain non-empty strings.")
    if len(codes) != len(set(codes)):
        raise ValueError("zone_codes must not contain duplicates.")
    return codes


def _parse_observation(item: dict, index: int) -> MetricObservation:
    value = item.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise InvalidGriddResponse(f"Observation entry {index} has an invalid value.")
    unit = item.get("unit")
    quality_status = item.get("quality_status")
    if not isinstance(unit, str) or not unit:
        raise InvalidGriddResponse(f"Observation entry {index} has no valid unit.")
    if not isinstance(quality_status, str) or not quality_status:
        raise InvalidGriddResponse(f"Observation entry {index} has no quality status.")
    try:
        observed_at = parse_utc_timestamp(item.get("observed_at"), "observed_at", optional=True)
        received_at = parse_utc_timestamp(item.get("received_at"), "received_at")
    except TimestampFormatError as exc:
        raise InvalidGriddResponse(f"Observation entry {index}: {exc}") from exc
    assert received_at is not None
    return MetricObservation(
        value=float(value),
        unit=unit,
        observed_at=observed_at,
        received_at=received_at,
        quality_status=quality_status,
    )
