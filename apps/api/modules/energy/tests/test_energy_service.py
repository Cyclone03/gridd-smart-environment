from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from modules.database.models import EnergyEstimate, EnergyProfile, Sensor, ThresholdProfile, Zone
from tests.support.sensor_pipeline import SensorPipeline


class EnergyServiceTests(TestCase):
    """Chaîne complète : mesures → ingestion → database → energy → database, puis API."""

    def setUp(self):
        self.zone = Zone.objects.create(name="Bureau", code="bureau", zone_type="office")
        ThresholdProfile.objects.create(zone=self.zone, enabled=False)
        Sensor.objects.create(node_id="t1", sensor_type="temperature", zone=self.zone, unit="°C")
        Sensor.objects.create(node_id="o1", sensor_type="occupancy", zone=self.zone, unit="count")
        self.pipeline = SensorPipeline()
        self.client = APIClient()
        self.t0 = timezone.now() - timedelta(minutes=30)

    def ingest(self, metric, value, minutes):
        node, unit = ("t1", "°C") if metric == "temperature" else ("o1", "count")
        return self.pipeline.ingest(
            node_id=node,
            observation_type=metric,
            value=value,
            unit=unit,
            observed_at=self.t0 + timedelta(minutes=minutes),
            metadata={"zone": {"id": "bureau", "label": "Bureau"}},
        )

    def test_each_reading_closes_an_interval_estimated_with_the_inputs_known_at_its_start(self):
        self.ingest("temperature", 22, 0)
        self.assertFalse(EnergyEstimate.objects.exists(), "la première mesure n'ouvre qu'un intervalle")
        self.ingest("occupancy", 3, 5)
        closing = self.ingest("temperature", 22, 10)

        first, second = EnergyEstimate.objects.order_by("end")
        self.assertEqual((first.duration_seconds, first.occupancy, first.occupancy_source), (300, 1, "profile"))
        self.assertEqual((second.occupancy, second.occupancy_source, second.observation), (3, "sensor", closing))
        self.assertEqual(second.indoor_temperature, 22)
        # 5 min à 3 occupants : éclairage 160 W, équipements 150 + 3 × 120 W.
        self.assertAlmostEqual(second.lighting_wh, 160 / 12, places=2)
        self.assertAlmostEqual(second.equipment_wh, 510 / 12, places=2)

    def test_simultaneous_readings_close_a_single_interval(self):
        for minutes in (0, 2, 4):
            self.ingest("temperature", 22, minutes)
            self.ingest("occupancy", 2, minutes)
        estimates = EnergyEstimate.objects.order_by("end")
        self.assertEqual([estimate.duration_seconds for estimate in estimates], [120, 120])
        self.assertEqual(sum(estimate.duration_seconds for estimate in estimates), 240)

    @override_settings(ENERGY_MAX_INTERVAL_MINUTES=15)
    def test_long_gaps_and_late_readings_are_not_estimated(self):
        self.ingest("temperature", 22, 0)
        self.ingest("temperature", 22, 20)  # capteur muet pendant 20 min
        self.assertFalse(EnergyEstimate.objects.exists())
        self.ingest("temperature", 22, 25)
        self.ingest("temperature", 22, 22)  # en retard
        self.assertEqual(EnergyEstimate.objects.count(), 1)

    def test_summary_and_series_endpoints(self):
        for minutes in (0, 10, 20):
            self.ingest("temperature", 21, minutes)

        summary = self.client.get("/api/energy/summary/", {"hours": 1}).json()
        zone = next(item for item in summary["zones"] if item["zone_code"] == "bureau")
        self.assertEqual(zone["covered_hours"], round(20 / 60, 2))
        self.assertGreater(zone["total_kwh"], 0)
        self.assertEqual(summary["total"]["total_kwh"], zone["total_kwh"])

        series = self.client.get("/api/energy/zones/bureau/series/", {"hours": 1}).json()
        self.assertEqual(series["bucket_minutes"], 5)
        self.assertAlmostEqual(sum(point["total_kwh"] for point in series["points"]), zone["total_kwh"], places=3)
        self.assertEqual(self.client.get("/api/energy/zones/inconnue/series/").status_code, 404)

    def test_profile_customization(self):
        url = "/api/energy/profiles/bureau/"
        default = self.client.get(url).json()
        self.assertEqual((default["customized"], default["profile"]["floor_area_m2"]), (False, 20))

        response = self.client.patch(url, {"floor_area_m2": 40, "equipment_base_w": 0}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        stored = EnergyProfile.objects.get(zone=self.zone)
        self.assertEqual((stored.floor_area_m2, stored.lighting_w_per_m2), (40, 8))

        self.ingest("temperature", 22, 0)
        self.ingest("temperature", 22, 6)
        self.assertAlmostEqual(EnergyEstimate.objects.get().lighting_wh, 40 * 8 / 10, places=2)

        self.assertEqual(self.client.patch(url, {"heating_cop": 0}, format="json").status_code, 400)
        self.assertFalse(self.client.delete(url).json()["customized"])
        self.assertFalse(EnergyProfile.objects.exists())
