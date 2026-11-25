from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from django.test import SimpleTestCase, TestCase

from modules.database.models import ClimatePrediction, Zone
from modules.database.models import WeatherSnapshot as WeatherSnapshotRecord
from modules.ia import composition
from modules.ia.adapters.messaging.event_bus_prediction_publisher import EventBusPredictionPublisher
from modules.ia.core.domain.climate_prediction_event import ClimatePredictionEvent
from modules.ia.core.domain.weather_point import WeatherPoint
from modules.ia.core.domain.weather_snapshot import WeatherSnapshot
from modules.ia.core.domain.weather_snapshot_event import WeatherSnapshotEvent
from modules.ia.core.errors import PredictionPublicationError
from shared.messaging import MessagingUnavailable


class EventBusIntegrationTests(TestCase):
    """Chaîne complète avec le bus mémoire : module IA → bus → module Database."""

    def setUp(self):
        self.zone = Zone.objects.create(name="Espace ouvert", code="open-workspace")
        self.publisher = composition.prediction_publisher()
        self.now = datetime.now(timezone.utc).replace(microsecond=0)

    def test_prediction_is_persisted_by_the_database_module(self):
        event = ClimatePredictionEvent.create(
            zone_code="open-workspace",
            generated_at=self.now,
            target_at=self.now + timedelta(hours=1),
            predicted_temperature_c=22.4,
            predicted_humidity_percent=41.0,
            model_version="modelZone1:sha256:test",
            prediction_mode="experimental",
        )

        receipt = self.publisher.publish_prediction(event)

        prediction = ClimatePrediction.objects.get(event_id=event.event_id)
        self.assertEqual((prediction.zone, prediction.predicted_temperature_c), (self.zone, 22.4))
        self.assertEqual((receipt.event_id, receipt.zone_code), (event.event_id, "open-workspace"))
        self.assertEqual(receipt.topic, "gridd.backend.ai_prediction.events")

    def test_weather_snapshot_is_persisted_by_the_database_module(self):
        current_at = self.now.replace(minute=0, second=0)
        event = WeatherSnapshotEvent.create(
            snapshot=WeatherSnapshot(
                current=WeatherPoint(current_at, 18.0, 60.0),
                forecast_h1=WeatherPoint(current_at + timedelta(hours=1), 17.5, 62.0),
            ),
            generated_at=current_at + timedelta(minutes=5),
        )

        self.publisher.publish_weather_snapshot(event)

        self.assertEqual(WeatherSnapshotRecord.objects.get(event_id=event.event_id).current_temperature_c, 18.0)


class EventBusPublisherErrorTests(SimpleTestCase):
    def test_bus_failure_becomes_a_publication_error(self):
        bus = Mock()
        bus.publish.side_effect = MessagingUnavailable("délai dépassé")
        now = datetime.now(timezone.utc)
        event = ClimatePredictionEvent.create(
            zone_code="meeting-room",
            generated_at=now,
            target_at=now + timedelta(hours=1),
            predicted_temperature_c=21.0,
            predicted_humidity_percent=40.0,
            model_version="m",
            prediction_mode="experimental",
        )

        with self.assertLogs("modules.ia", level="ERROR"), self.assertRaises(PredictionPublicationError):
            EventBusPredictionPublisher(bus, topic="t").publish_prediction(event)
        (topic, envelope), kwargs = bus.publish.call_args
        self.assertEqual((topic, envelope.event_id, kwargs["key"]), ("t", event.event_id, "meeting-room"))
