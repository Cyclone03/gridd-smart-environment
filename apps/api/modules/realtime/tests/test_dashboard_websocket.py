from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from modules.database.models import Alert, Observation, Sensor, Zone
from modules.realtime.routing import websocket_urlpatterns

IN_MEMORY_LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class DashboardWebSocketTests(TransactionTestCase):
    """``/ws/dashboard/`` fournit toutes les données du tableau de bord :
    instantané à la connexion, puis changements poussés avec leurs données."""

    def setUp(self):
        self.zone = Zone.objects.create(name="Salle", code="salle")
        Zone.objects.create(name="Inactive", code="inactive", active=False)
        sensor = Sensor.objects.create(node_id="n1", sensor_type="temperature", zone=self.zone, unit="°C")
        now = timezone.now()
        Observation.objects.create(
            sensor=sensor,
            zone=self.zone,
            type="temperature",
            value=20,
            unit="°C",
            observed_at=now - timedelta(minutes=2),
        )
        self.latest = Observation.objects.create(
            sensor=sensor, zone=self.zone, type="temperature", value=21.5, unit="°C", observed_at=now
        )
        self.active = Alert.objects.create(zone=self.zone, code="Y", message="en cours", severity="critical")
        self.resolved = Alert.objects.create(
            zone=self.zone, code="X", message="terminée", severity="warning", active=False, resolved_at=now
        )
        Alert.objects.create(
            zone=self.zone,
            code="Z",
            message="trop ancienne",
            severity="info",
            active=False,
            created_at=now - timedelta(days=30),
        )

    async def connect(self):
        communicator = WebsocketCommunicator(URLRouter(websocket_urlpatterns), "/ws/dashboard/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        self.assertEqual(await communicator.receive_json_from(), {"event": "realtime.connected"})
        return communicator

    def test_sends_a_complete_snapshot_on_connect_and_on_demand(self):
        async def scenario():
            communicator = await self.connect()
            snapshot = await communicator.receive_json_from(timeout=5)
            await communicator.send_json_to({"action": "snapshot"})
            again = await communicator.receive_json_from(timeout=5)
            await communicator.send_json_to({"action": "ping"})
            pong = await communicator.receive_json_from()
            await communicator.disconnect()
            return snapshot, again, pong

        snapshot, again, pong = async_to_sync(scenario)()
        self.assertEqual(snapshot["event"], "dashboard.snapshot")
        data = snapshot["data"]
        self.assertEqual([zone["code"] for zone in data["zones"]], ["salle"])
        self.assertEqual(data["zones"][0]["metrics"], ["temperature"])
        self.assertEqual([item["id"] for item in data["latest"]], [self.latest.id])
        self.assertEqual(data["latest"][0]["zone_code"], "salle")
        self.assertEqual([alert["id"] for alert in data["alerts"]["active"]], [self.active.id])
        self.assertEqual([alert["id"] for alert in data["alerts"]["history"]], [self.resolved.id])
        self.assertEqual(again, snapshot)
        self.assertEqual(pong, {"event": "pong"})

    def test_pushes_alerts_and_zones_with_their_data(self):
        prediction = {
            "prediction_id": 17,
            "prediction_event_id": "4b9ab2a9-98a8-47d1-92d0-b794957ca4a7",
            "zone_code": "salle",
            "generated_at": "2026-11-15T18:00:00+00:00",
            "target_at": "2026-11-15T19:00:00+00:00",
            "predicted_temperature_c": 23.5,
            "predicted_humidity_percent": 45.0,
            "model_version": "zone-1-test",
            "prediction_mode": "experimental",
        }
        weather = {
            "weather_snapshot_id": 8,
            "weather_snapshot_event_id": "88b8053b-634b-4a43-92b0-c22bed310001",
            "generated_at": "2026-11-15T18:00:00+00:00",
            "provider": "open-meteo",
            "current_at": "2026-11-15T18:00:00+00:00",
            "current_temperature_c": 18.5,
            "current_relative_humidity_percent": 55.0,
            "forecast_h1_at": "2026-11-15T19:00:00+00:00",
            "forecast_h1_temperature_c": 19.0,
            "forecast_h1_relative_humidity_percent": 57.0,
        }

        async def scenario():
            communicator = await self.connect()
            await communicator.receive_json_from(timeout=5)  # instantané
            layer = get_channel_layer()
            await layer.group_send("dashboard", {"type": "alerts.changed", "payload": {"active": [], "history": []}})
            alerts = await communicator.receive_json_from()
            await layer.group_send("dashboard", {"type": "zones.changed", "payload": [{"code": "salle"}]})
            zones = await communicator.receive_json_from()
            await layer.group_send(
                "dashboard",
                {"type": "climate_prediction.created", "payload": prediction},
            )
            climate_prediction = await communicator.receive_json_from()
            await layer.group_send(
                "dashboard",
                {"type": "weather_snapshot.created", "payload": weather},
            )
            weather_snapshot = await communicator.receive_json_from()
            await layer.group_send("dashboard", {"type": "observations.created", "payload": [{"id": 1}]})
            batch = await communicator.receive_json_from()
            await communicator.disconnect()
            return alerts, zones, climate_prediction, weather_snapshot, batch

        alerts, zones, climate_prediction, weather_snapshot, batch = async_to_sync(scenario)()
        self.assertEqual(alerts, {"event": "alerts.changed", "data": {"active": [], "history": []}})
        self.assertEqual(batch, {"event": "observations.created", "data": [{"id": 1}]})
        self.assertEqual(zones, {"event": "zones.changed", "data": [{"code": "salle"}]})
        self.assertEqual(
            climate_prediction,
            {"event": "climate_prediction.created", "data": prediction},
        )
        self.assertEqual(
            weather_snapshot,
            {"event": "weather_snapshot.created", "data": weather},
        )
