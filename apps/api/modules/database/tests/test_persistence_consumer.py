import uuid
from datetime import timedelta
from unittest.mock import patch

from django.apps import apps
from django.db import OperationalError
from django.test import TestCase, override_settings
from django.utils import timezone

from modules.database.composition import persistence_consumer
from modules.database.models import AlarmRule, Alert, ClimatePrediction, Observation, WeatherSnapshot, Zone
from shared.contracts.topics import Topics
from shared.kernel.events.event_types import EventTypes
from shared.messaging import Event, InboundMessage, MessageRejected


class RecordingPublisher:
    is_synchronous = True

    def __init__(self):
        self.published = []

    def publish(self, topic, event, key=None):
        self.published.append((topic, event))


class PersistenceConsumerTests(TestCase):
    """Le module Database applique les événements et commandes qu'il reçoit,
    de façon idempotente, et répond toujours aux commandes."""

    def setUp(self):
        self.publisher = RecordingPublisher()
        self.consumer = persistence_consumer(publisher=self.publisher)

    def deliver(self, event, topic=None):
        self.consumer.handle(InboundMessage(topic=topic or Topics.ingestion_observations(), value=event.encode()))

    def published(self, event_type):
        return [event for _, event in self.publisher.published if event.type == event_type]

    def observation_event(self, event_id):
        now = timezone.now().isoformat()
        payload = {
            "event_id": event_id,
            "node_id": "n1",
            "metric": "temperature",
            "value": 21.5,
            "unit": "°C",
            "observed_at": now,
            "received_at": now,
            "metadata": {"source": "test"},
            "sensor_metadata": {"source": "test"},
            "quality_status": "normal",
            "quality_reason": "",
            "zone": {"code": "salle", "name": "Salle", "type": None},
        }
        return Event(type=EventTypes.OBSERVATION_VALIDATED, payload=payload, source="ingestion")

    def prediction_event(
        self,
        *,
        event_id=None,
        prediction_mode="experimental",
        zone_code="open-workspace",
        generated_at=None,
    ):
        generated = generated_at or timezone.now().replace(microsecond=0)
        return Event(
            type=EventTypes.CLIMATE_PREDICTION_GENERATED,
            payload={
                "zone_code": zone_code,
                "generated_at": generated.isoformat(),
                "target_at": (generated + timedelta(hours=1)).isoformat(),
                "predicted_temperature_c": 23.5,
                "predicted_humidity_percent": 45.0,
                "model_version": "zone-1-test",
                "prediction_mode": prediction_mode,
            },
            source="ai_prediction_service",
            event_id=event_id or str(uuid.uuid4()),
            occurred_at=generated.isoformat(),
        )

    def weather_snapshot_event(self, *, event_id=None, generated_at=None):
        generated = generated_at or timezone.now().replace(microsecond=0)
        return Event(
            type=EventTypes.WEATHER_SNAPSHOT_GENERATED,
            payload={
                "generated_at": generated.isoformat(),
                "provider": "open-meteo",
                "current_at": generated.isoformat(),
                "current_temperature_c": 18.5,
                "current_relative_humidity_percent": 55.0,
                "forecast_h1_at": (generated + timedelta(hours=1)).isoformat(),
                "forecast_h1_temperature_c": 19.0,
                "forecast_h1_relative_humidity_percent": 57.0,
            },
            source="ai_prediction_service",
            event_id=event_id or str(uuid.uuid4()),
            occurred_at=generated.isoformat(),
        )

    def test_zones_changed_is_published_only_when_the_zone_list_changes(self):
        def deliver(node_id, name="Salle"):
            event = self.observation_event(str(uuid.uuid4()))
            event.payload["node_id"] = node_id
            event.payload["zone"]["name"] = name
            self.deliver(event)

        deliver("n1")  # nouvelle zone et nouveau capteur
        self.assertEqual(len(self.published(EventTypes.ZONES_CHANGED)), 1)
        deliver("n1")  # rien de nouveau
        self.assertEqual(len(self.published(EventTypes.ZONES_CHANGED)), 1)
        deliver("n2")  # nouveau capteur
        deliver("n2", name="Salle B")  # zone renommée
        self.assertEqual(len(self.published(EventTypes.ZONES_CHANGED)), 3)
        self.assertEqual(self.published(EventTypes.ZONES_CHANGED)[0].payload, {"zone_code": "salle"})

    def test_redelivered_observation_is_persisted_once(self):
        event = self.observation_event(str(uuid.uuid4()))
        self.deliver(event)
        self.deliver(event)
        self.assertEqual(Observation.objects.count(), 1)
        self.assertEqual(Zone.objects.get(code="salle").zone_type, Zone.ZoneType.OTHER)
        persisted = self.published(EventTypes.OBSERVATION_PERSISTED)
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0].payload["zone_code"], "salle")

    def test_climate_prediction_is_persisted_and_published_after_insert(self):
        zone = Zone.objects.create(name="Espace ouvert", code="open-workspace")
        event = self.prediction_event()
        original_publish = self.publisher.publish

        def assert_persisted_before_publish(topic, published_event, key=None):
            self.assertEqual(ClimatePrediction.objects.count(), 1)
            self.assertEqual(topic, Topics.database_events())
            self.assertEqual(key, zone.code)
            original_publish(topic, published_event, key)

        with patch.object(self.publisher, "publish", side_effect=assert_persisted_before_publish):
            self.deliver(event, topic=Topics.ai_prediction_events())

        prediction = ClimatePrediction.objects.get()
        self.assertEqual(prediction.zone, zone)
        self.assertEqual(prediction.event_id, uuid.UUID(event.event_id))
        self.assertEqual(prediction.prediction_mode, ClimatePrediction.PredictionMode.EXPERIMENTAL)
        persisted = self.published(EventTypes.CLIMATE_PREDICTION_PERSISTED)
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0].payload["prediction_event_id"], event.event_id)
        self.assertEqual(persisted[0].payload["prediction_id"], prediction.pk)

    def test_prediction_modes_are_persisted_distinctly(self):
        Zone.objects.create(name="Espace ouvert", code="open-workspace")
        for mode in ("experimental", "operational"):
            self.deliver(self.prediction_event(prediction_mode=mode))
        self.assertCountEqual(
            ClimatePrediction.objects.values_list("prediction_mode", flat=True),
            ["experimental", "operational"],
        )

    def test_redelivered_prediction_is_persisted_and_published_once(self):
        Zone.objects.create(name="Espace ouvert", code="open-workspace")
        event = self.prediction_event()
        self.deliver(event, topic=Topics.ai_prediction_events())
        self.deliver(event, topic=Topics.ai_prediction_events())
        self.assertEqual(ClimatePrediction.objects.count(), 1)
        self.assertEqual(len(self.published(EventTypes.CLIMATE_PREDICTION_PERSISTED)), 1)

    def test_invalid_prediction_contract_and_unknown_zone_are_rejected(self):
        Zone.objects.create(name="Espace ouvert", code="open-workspace")
        Zone.objects.create(name="Zone inactive", code="inactive-zone", active=False)
        invalid_events = [
            self.prediction_event(zone_code="unknown-zone"),
            self.prediction_event(zone_code="inactive-zone"),
            self.prediction_event(prediction_mode="preview"),
            self.prediction_event(generated_at=timezone.now().replace(tzinfo=None)),
            self.prediction_event(),
            self.prediction_event(),
        ]
        invalid_events[0].payload["zone_code"] = "unknown-zone"
        invalid_events[1].payload["zone_code"] = "inactive-zone"
        invalid_events[2].payload["prediction_mode"] = "preview"
        invalid_events[3].payload["generated_at"] = "2026-01-01T10:00:00"
        del invalid_events[4].payload["model_version"]
        invalid_events[5].payload["predicted_humidity_percent"] = float("nan")
        for event in invalid_events:
            with self.subTest(payload=event.payload):
                with self.assertRaises(MessageRejected):
                    self.deliver(event, topic=Topics.ai_prediction_events())
        self.assertEqual(ClimatePrediction.objects.count(), 0)
        self.assertEqual(self.published(EventTypes.CLIMATE_PREDICTION_PERSISTED), [])

    def test_reused_event_id_with_different_values_is_rejected(self):
        Zone.objects.create(name="Espace ouvert", code="open-workspace")
        event = self.prediction_event()
        self.deliver(event, topic=Topics.ai_prediction_events())
        changed = Event(
            type=event.type,
            payload={**event.payload, "predicted_temperature_c": 24.0},
            source=event.source,
            event_id=event.event_id,
            occurred_at=event.occurred_at,
        )
        with self.assertRaises(MessageRejected):
            self.deliver(changed, topic=Topics.ai_prediction_events())
        self.assertEqual(ClimatePrediction.objects.count(), 1)
        self.assertEqual(len(self.published(EventTypes.CLIMATE_PREDICTION_PERSISTED)), 1)

    def test_database_error_does_not_publish_prediction_persisted(self):
        Zone.objects.create(name="Espace ouvert", code="open-workspace")
        event = self.prediction_event()
        with patch(
            "modules.database.adapters.persistence.climate_prediction_writer.ClimatePrediction.objects.get_or_create",
            side_effect=OperationalError("isolated database failure"),
        ):
            with self.assertRaises(OperationalError):
                self.deliver(event, topic=Topics.ai_prediction_events())
        self.assertEqual(self.published(EventTypes.CLIMATE_PREDICTION_PERSISTED), [])

    def test_weather_snapshot_is_persisted_idempotently_and_published(self):
        event = self.weather_snapshot_event()
        self.deliver(event, topic=Topics.ai_prediction_events())
        self.deliver(event, topic=Topics.ai_prediction_events())

        snapshot = WeatherSnapshot.objects.get()
        persisted = self.published(EventTypes.WEATHER_SNAPSHOT_PERSISTED)
        self.assertEqual(WeatherSnapshot.objects.count(), 1)
        self.assertEqual(snapshot.event_id, uuid.UUID(event.event_id))
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0].payload["weather_snapshot_id"], snapshot.pk)
        self.assertEqual(persisted[0].payload["weather_snapshot_event_id"], event.event_id)

    def test_invalid_weather_snapshot_contract_is_rejected(self):
        invalid_events = [
            self.weather_snapshot_event(),
            self.weather_snapshot_event(),
            self.weather_snapshot_event(),
            self.weather_snapshot_event(),
            self.weather_snapshot_event(),
        ]
        invalid_events[0].payload["provider"] = "other-provider"
        invalid_events[1].payload["forecast_h1_at"] = invalid_events[1].payload["generated_at"]
        invalid_events[2].payload["current_relative_humidity_percent"] = 101
        invalid_events[3].payload["forecast_h1_temperature_c"] = float("nan")
        del invalid_events[4].payload["current_at"]

        for event in invalid_events:
            with self.subTest(payload=event.payload):
                with self.assertRaises(MessageRejected):
                    self.deliver(event, topic=Topics.ai_prediction_events())

        self.assertEqual(WeatherSnapshot.objects.count(), 0)
        self.assertEqual(self.published(EventTypes.WEATHER_SNAPSHOT_PERSISTED), [])

    def test_publisher_error_is_not_swallowed_after_successful_persistence(self):
        Zone.objects.create(name="Espace ouvert", code="open-workspace")
        event = self.prediction_event()
        with patch.object(
            self.publisher,
            "publish",
            side_effect=RuntimeError("isolated publisher failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.deliver(event, topic=Topics.ai_prediction_events())
        self.assertEqual(ClimatePrediction.objects.count(), 1)


    def test_alert_raised_twice_keeps_a_single_active_alert(self):
        Zone.objects.create(name="Salle", code="salle")
        payload = {
            "zone_code": "salle",
            "code": "DATA_QUALITY_TEMPERATURE",
            "rule_id": None,
            "severity": "warning",
            "message": "Donnée suspecte",
            "trigger_value": 30,
            "observation_id": None,
            "refresh_fields": ["message", "severity"],
        }
        for _ in range(2):
            self.deliver(Event(type=EventTypes.ALERT_RAISED, payload=payload, source="alarms"))
        self.assertEqual(Alert.objects.filter(active=True).count(), 1)
        self.assertEqual(len(self.published(EventTypes.ALERTS_CHANGED)), 1)

    def command(self, command_type, payload):
        return Event(
            type=command_type,
            payload=payload,
            source="test",
            correlation_id="c-1",
            reply_to=Topics.database_replies(),
        )

    def test_command_success_and_failure_are_answered(self):
        fields = {"name": "R", "metric": "temperature", "operator": "gt", "threshold": 25, "zone": None}
        self.deliver(self.command(EventTypes.ALARM_RULE_CREATE, {"fields": fields}))
        rule = AlarmRule.objects.get()
        succeeded = self.published(EventTypes.COMMAND_SUCCEEDED)
        self.assertEqual(succeeded[0].payload, {"data": {"rule_id": rule.pk}})
        self.assertEqual(succeeded[0].correlation_id, "c-1")
        changed = self.published(EventTypes.ALARM_RULE_CHANGED)
        self.assertEqual(changed[0].payload["action"], "created")

        self.deliver(self.command(EventTypes.ALARM_RULE_DELETE, {"rule_id": 999}))
        failed = self.published(EventTypes.COMMAND_FAILED)
        self.assertEqual(failed[0].payload["error"]["code"], "not_found")

        self.deliver(self.command(EventTypes.ALARM_RULE_UPDATE, {"rule_id": rule.pk, "fields": {"zone": "inconnue"}}))
        errors = self.published(EventTypes.COMMAND_FAILED)[1].payload["error"]["errors"]
        self.assertEqual(errors, {"zone": ["Zone inconnue ou inactive."]})



class BatchPersistenceTests(PersistenceConsumerTests):
    """Lot Kafka : les observations sont enregistrées ensemble à la fin du lot."""

    def test_batch_is_persisted_once_with_duplicates_ignored(self):
        events = [self.observation_event(str(uuid.uuid4())) for _ in range(20)]
        self.consumer.begin_batch()
        for event in events + events[:5]:  # 5 messages relivrés dans le même lot
            self.deliver(event)
        self.assertEqual(Observation.objects.count(), 0)  # rien avant la fin du lot
        self.consumer.end_batch()
        self.assertEqual(Observation.objects.count(), 20)
        self.assertEqual(len(self.published(EventTypes.OBSERVATION_PERSISTED)), 20)
        self.assertEqual(len(self.published(EventTypes.ZONES_CHANGED)), 1)

        # Lot relu après un échec : aucun doublon, rien de republié.
        self.consumer.begin_batch()
        for event in events:
            self.deliver(event)
        self.consumer.end_batch()
        self.assertEqual(Observation.objects.count(), 20)
        self.assertEqual(len(self.published(EventTypes.OBSERVATION_PERSISTED)), 20)

    def test_known_zones_and_sensors_are_not_read_again(self):
        consumer = persistence_consumer(publisher=self.publisher)
        consumer._observations._cache_references = True
        warmup = self.observation_event(str(uuid.uuid4()))
        consumer.handle(InboundMessage(topic=Topics.ingestion_observations(), value=warmup.encode()))

        consumer.begin_batch()
        for _ in range(100):
            event = self.observation_event(str(uuid.uuid4()))
            consumer.handle(InboundMessage(topic=Topics.ingestion_observations(), value=event.encode()))
        # Transaction + recherche des doublons + insertion groupée, pour 100 mesures.
        with self.assertNumQueries(4):
            consumer.end_batch()
        self.assertEqual(Observation.objects.count(), 101)


class DatabasePredictionSubscriptionTests(TestCase):
    @override_settings(
        DATABASE_SUBSCRIBED_TOPICS=["gridd.backend.ai_prediction.events"],
        KAFKA_TOPICS={"alarms_commands": "gridd.backend.alarms.commands"},
    )
    def test_database_subscribes_to_the_ai_prediction_topic(self):
        subscriptions = apps.get_app_config("core").subscriptions()
        self.assertEqual(len(subscriptions), 1)
        self.assertEqual(
            subscriptions[0].topics,
            ("gridd.backend.ai_prediction.events",),
        )
