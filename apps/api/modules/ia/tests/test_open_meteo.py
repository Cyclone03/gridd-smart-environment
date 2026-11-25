import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

from modules.ia.adapters.http.http_json import fetch_json
from modules.ia.adapters.http.open_meteo_weather_source import OpenMeteoWeatherSource
from modules.ia.core.errors import HttpRequestError, IncompleteWeatherResponse, OpenMeteoError


class OpenMeteoClientTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "current": {
                "time": "2026-11-13T21:20:00Z",
                "temperature_2m": 14.5,
                "relative_humidity_2m": 72,
            },
            "hourly": {
                "time": ["2026-11-13T21:00", "2026-11-13T22:00"],
                "temperature_2m": [14.0, 13.2],
                "relative_humidity_2m": [73, 78],
            },
        }
        self.transport = Mock(return_value=self.payload)
        self.client = OpenMeteoWeatherSource(
            45.5,
            -73.6,
            transport=self.transport,
        )

    def test_fetch_returns_current_and_next_utc_hour_forecast(self):
        result = self.client.fetch()

        self.assertEqual(result.current.timestamp_utc, datetime(2026, 11, 13, 21, 20, tzinfo=timezone.utc))
        self.assertEqual(result.current.temperature_c, 14.5)
        self.assertEqual(result.forecast_h1.timestamp_utc, datetime(2026, 11, 13, 22, 0, tzinfo=timezone.utc))
        self.assertEqual(result.forecast_h1.relative_humidity_pct, 78)
        url = self.transport.call_args.args[0]
        query = parse_qs(urlparse(url).query)
        self.assertEqual(query["timezone"], ["UTC"])
        self.assertEqual(query["latitude"], ["45.5"])
        self.assertEqual(query["longitude"], ["-73.6"])
        self.assertIn("relative_humidity_2m", query["current"][0])
        self.assertIn("relative_humidity_2m", query["hourly"][0])

    def test_network_failure_is_reported_as_open_meteo_error(self):
        self.transport.side_effect = HttpRequestError("network unavailable")

        with self.assertRaises(OpenMeteoError):
            self.client.fetch()

    @patch("modules.ia.adapters.http.http_json.urlopen", side_effect=URLError("offline"))
    def test_http_transport_wraps_connection_errors(self, _urlopen):
        with self.assertRaises(HttpRequestError):
            fetch_json("https://weather.test", timeout=1)

    def test_missing_humidity_is_rejected(self):
        self.payload["current"]["relative_humidity_2m"] = None

        with self.assertRaises(IncompleteWeatherResponse):
            self.client.fetch()

    def test_missing_h_plus_one_hour_is_rejected(self):
        self.payload["hourly"]["time"] = ["2026-11-13T21:00"]
        self.payload["hourly"]["temperature_2m"] = [14.0]
        self.payload["hourly"]["relative_humidity_2m"] = [73]

        with self.assertRaises(IncompleteWeatherResponse):
            self.client.fetch()

    def test_invalid_coordinate_is_rejected(self):
        with self.assertRaises(ValueError):
            OpenMeteoWeatherSource(91, -73.6)
