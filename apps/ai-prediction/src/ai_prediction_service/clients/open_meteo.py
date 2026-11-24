import math
from datetime import timedelta
from typing import Callable
from urllib.parse import urlencode

from ..domain.timestamps import parse_utc_timestamp
from ..domain.weather import WeatherPoint, WeatherSnapshot
from ..errors import (
    HttpRequestError,
    IncompleteWeatherResponse,
    OpenMeteoError,
    TimestampFormatError,
)
from ..http_json import fetch_json

JsonTransport = Callable[..., object]


class OpenMeteoClient:
    ENDPOINT = "https://api.open-meteo.com/v1/forecast"
    WEATHER_VARIABLES = "temperature_2m,relative_humidity_2m"

    def __init__(
        self,
        latitude: float,
        longitude: float,
        *,
        timeout_seconds: float = 10.0,
        endpoint: str = ENDPOINT,
        transport: JsonTransport = fetch_json,
    ):
        if not math.isfinite(latitude) or not -90 <= latitude <= 90:
            raise ValueError("latitude must be finite and between -90 and 90.")
        if not math.isfinite(longitude) or not -180 <= longitude <= 180:
            raise ValueError("longitude must be finite and between -180 and 180.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")
        self._latitude = latitude
        self._longitude = longitude
        self._timeout_seconds = timeout_seconds
        self._endpoint = endpoint
        self._transport = transport

    def fetch(self) -> WeatherSnapshot:
        query = urlencode(
            {
                "latitude": self._latitude,
                "longitude": self._longitude,
                "current": self.WEATHER_VARIABLES,
                "hourly": self.WEATHER_VARIABLES,
                "forecast_days": 2,
                "temperature_unit": "celsius",
                "timezone": "UTC",
            }
        )
        try:
            payload = self._transport(f"{self._endpoint}?{query}", timeout=self._timeout_seconds)
        except HttpRequestError as exc:
            raise OpenMeteoError("Open-Meteo request failed.") from exc

        if not isinstance(payload, dict):
            raise IncompleteWeatherResponse("Open-Meteo response must be a JSON object.")
        if payload.get("error"):
            reason = payload.get("reason")
            raise OpenMeteoError(f"Open-Meteo reported an error: {reason or 'unspecified error'}.")

        current = payload.get("current")
        if not isinstance(current, dict):
            raise IncompleteWeatherResponse("Open-Meteo response is missing current conditions.")

        try:
            current_at = parse_utc_timestamp(current.get("time"), "current.time", assume_utc=True)
        except TimestampFormatError as exc:
            raise IncompleteWeatherResponse(str(exc)) from exc
        assert current_at is not None
        current_point = WeatherPoint(
            timestamp_utc=current_at,
            temperature_c=_weather_number(current.get("temperature_2m"), "current.temperature_2m"),
            relative_humidity_pct=_humidity_number(
                current.get("relative_humidity_2m"), "current.relative_humidity_2m"
            ),
        )

        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            raise IncompleteWeatherResponse("Open-Meteo response is missing hourly forecasts.")
        times = hourly.get("time")
        temperatures = hourly.get("temperature_2m")
        humidities = hourly.get("relative_humidity_2m")
        if not all(isinstance(items, list) for items in (times, temperatures, humidities)):
            raise IncompleteWeatherResponse("Hourly forecast fields must be arrays.")
        if not times or len(times) != len(temperatures) or len(times) != len(humidities):
            raise IncompleteWeatherResponse("Hourly forecast arrays are empty or have different lengths.")

        forecast_at = current_at.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        forecast_values = []
        for index, value in enumerate(times):
            try:
                timestamp = parse_utc_timestamp(value, f"hourly.time[{index}]", assume_utc=True)
            except TimestampFormatError as exc:
                raise IncompleteWeatherResponse(str(exc)) from exc
            if timestamp == forecast_at:
                forecast_values.append((temperatures[index], humidities[index]))

        if len(forecast_values) != 1:
            raise IncompleteWeatherResponse(
                f"Expected one hourly forecast at {forecast_at.isoformat()}, found {len(forecast_values)}."
            )
        temperature, humidity = forecast_values[0]
        forecast_point = WeatherPoint(
            timestamp_utc=forecast_at,
            temperature_c=_weather_number(temperature, "hourly.temperature_2m"),
            relative_humidity_pct=_humidity_number(humidity, "hourly.relative_humidity_2m"),
        )
        return WeatherSnapshot(current=current_point, forecast_h1=forecast_point)


def _weather_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise IncompleteWeatherResponse(f"{field} must be a finite number.")
    return float(value)


def _humidity_number(value: object, field: str) -> float:
    humidity = _weather_number(value, field)
    if not 0 <= humidity <= 100:
        raise IncompleteWeatherResponse(f"{field} must be between 0 and 100.")
    return humidity
