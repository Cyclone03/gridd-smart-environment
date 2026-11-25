from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from modules.ia.core.domain.weather_point import WeatherPoint
from modules.ia.core.domain.weather_snapshot import WeatherSnapshot
from modules.ia.core.domain.weather_snapshot_event import WeatherSnapshotEvent
from modules.ia.core.domain.zones import ZONE_MODEL_MAPPING
from modules.ia.core.services.prediction_cycle import PredictionCycle


class FakeRegistry:
    def zone_codes(self):
        return tuple(ZONE_MODEL_MAPPING.values())

    def for_zone(self, zone_code):
        artifact = SimpleNamespace(sha256="0" * 64, path=None)
        return SimpleNamespace(zone_code=zone_code, model=artifact, scaler_x=artifact, scaler_y=artifact)


class PredictionCycleTests(SimpleTestCase):
    def test_publishes_weather_and_skips_inference_when_no_model_bundle_loads(self):
        publisher = Mock()
        collection = Mock()
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        collection.fetch_weather.return_value = WeatherSnapshot(
            current=WeatherPoint(now, 18.0, 60.0),
            forecast_h1=WeatherPoint(now + timedelta(hours=1), 17.5, 62.0),
        )
        loader = Mock(side_effect=AssertionError("aucun artefact ne doit être chargé"))
        cycle = PredictionCycle(
            registry=FakeRegistry(),
            approved_scaler_sha256=frozenset(),
            isolated_environment=False,
            model_loader=loader,
            scaler_loader=loader,
            collection=collection,
            publisher=publisher,
        )

        with self.assertLogs("modules.ia", level="ERROR"):
            result = cycle.run()

        self.assertEqual(result, 1)
        collection.fetch_weather.assert_called_once_with()
        (event,), _ = publisher.publish_weather_snapshot.call_args
        self.assertIsInstance(event, WeatherSnapshotEvent)
        self.assertEqual(publisher.publish_prediction.call_count, 0)
        loader.assert_not_called()
