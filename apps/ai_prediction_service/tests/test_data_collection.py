import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from ai_prediction_service.domain.observations import MetricObservation, ZoneObservations
from ai_prediction_service.domain.weather import WeatherPoint, WeatherSnapshot
from ai_prediction_service.services.data_collection import DataCollectionService


class DataCollectionServiceTests(unittest.TestCase):
    def test_collect_combines_weather_and_internal_observations(self):
        weather_result = WeatherSnapshot(
            current=WeatherPoint(datetime(2026, 11, 13, 21, 0, tzinfo=timezone.utc), 14.0, 70.0),
            forecast_h1=WeatherPoint(datetime(2026, 11, 13, 22, 0, tzinfo=timezone.utc), 13.0, 75.0),
        )
        observation = MetricObservation(
            value=21.5,
            unit="°C",
            observed_at=datetime(2026, 11, 13, 21, 0, tzinfo=timezone.utc),
            received_at=datetime(2026, 11, 13, 21, 0, 2, tzinfo=timezone.utc),
            quality_status="normal",
        )
        zones_result = {
            "meeting-room": ZoneObservations(
                zone_code="meeting-room",
                temperature=observation,
                humidity=MetricObservation(42.0, "%", observation.observed_at, observation.received_at, "normal"),
            )
        }
        weather_client = Mock()
        weather_client.fetch.return_value = weather_result
        gridd_client = Mock()
        gridd_client.fetch_latest.return_value = zones_result
        service = DataCollectionService(weather=weather_client, observations=gridd_client)

        result = service.collect(("meeting-room",))

        self.assertEqual(result.weather, weather_result)
        self.assertEqual(result.zones, zones_result)
        self.assertIsNotNone(result.collected_at.tzinfo)
        weather_client.fetch.assert_called_once_with()
        gridd_client.fetch_latest.assert_called_once_with(("meeting-room",))


if __name__ == "__main__":
    unittest.main()
