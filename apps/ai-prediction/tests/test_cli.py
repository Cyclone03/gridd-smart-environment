import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai_prediction_service import cli


class PredictionServiceCliTests(unittest.TestCase):
    def test_publishes_weather_and_skips_inference_when_no_model_bundle_loads(self):
        registry = object()
        weather = object()
        producer = Mock()
        collection = Mock()
        collection.fetch_weather.return_value = weather

        with (
            patch.object(cli, "ArtifactRegistry", return_value=registry),
            patch.object(
                cli.ServiceSettings,
                "from_env",
                return_value=SimpleNamespace(
                    open_meteo_latitude=45.5,
                    open_meteo_longitude=-73.6,
                    http_timeout_seconds=10,
                    gridd_api_base_url="http://api",
                ),
            ),
            patch.object(cli, "OpenMeteoClient"),
            patch.object(cli, "GriddApiClient"),
            patch.object(cli, "DataCollectionService", return_value=collection),
            patch.object(cli.KafkaPredictionProducer, "from_env", return_value=producer),
            patch.object(cli, "load_model_predictor", side_effect=RuntimeError("unapproved scaler")),
        ):
            with self.assertLogs("ai_prediction_service", level="ERROR"):
                result = cli.main()

        self.assertEqual(result, 1)
        producer.publish_weather_snapshot.assert_called_once_with(weather)
        collection.fetch_weather.assert_called_once_with()
        self.assertEqual(producer.publish_prediction.call_count, 0)
