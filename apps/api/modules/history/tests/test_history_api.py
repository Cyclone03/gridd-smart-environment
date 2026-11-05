from datetime import datetime, timedelta

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from modules.database.models import Observation, Sensor, Zone


class LegacyHistoryApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.zone = Zone.objects.create(name="Bureau", code="bureau", zone_type="office")
        self.sensor = Sensor.objects.create(node_id="bureau-temperature", sensor_type="temperature", zone=self.zone, unit="°C")

    def test_history_returns_aggregates_for_requested_period(self):
        now = timezone.now()
        for offset, value in enumerate([21.0, 22.0, 23.0]):
            Observation.objects.create(
                sensor=self.sensor,
                zone=self.zone,
                type="temperature",
                value=value,
                unit="°C",
                observed_at=now - timedelta(minutes=30 - offset * 15),
            )

        response = self.client.get("/api/zones/bureau/history/?type=temperature&hours=24")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["hours"], 24)
        self.assertEqual(payload["statistics"]["minimum"], 21.0)
        self.assertEqual(payload["statistics"]["maximum"], 23.0)
        self.assertEqual(payload["statistics"]["average"], 22.0)
        self.assertEqual(payload["statistics"]["count"], 3)

    def test_history_can_target_one_exact_local_calendar_day(self):
        local_timezone = timezone.get_current_timezone()
        selected_day = timezone.localdate()
        day_start = timezone.make_aware(datetime.combine(selected_day, datetime.min.time()), local_timezone)
        for value, observed_at in ((22.0, day_start + timedelta(hours=10)), (99.0, day_start - timedelta(minutes=1))):
            Observation.objects.create(
                sensor=self.sensor, zone=self.zone, type="temperature", value=value, unit="°C", observed_at=observed_at
            )

        response = self.client.get(f"/api/zones/bureau/history/?type=temperature&date={selected_day.isoformat()}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["date"], selected_day.isoformat())
        self.assertEqual(payload["statistics"]["count"], 1)
        self.assertEqual(payload["statistics"]["average"], 22.0)


class PeriodHistoryApiTests(TestCase):
    """Contrat start/end/bucket_minutes des périodes configurables."""

    def setUp(self):
        self.client = Client()
        self.zone = Zone.objects.create(name="Bureau", code="bureau", zone_type="office")
        self.sensor = Sensor.objects.create(node_id="bureau-temperature", sensor_type="temperature", zone=self.zone, unit="C")
        self.now = timezone.now().replace(microsecond=0)

    def add(self, minutes_ago, value, **extra):
        return Observation.objects.create(
            sensor=self.sensor,
            zone=self.zone,
            type="temperature",
            value=value,
            unit="C",
            observed_at=self.now - timedelta(minutes=minutes_ago),
            **extra,
        )

    def get(self, **params):
        return self.client.get("/api/zones/bureau/history/", {"type": "temperature", **params})

    def test_returns_only_observations_inside_requested_bounds(self):
        self.add(90, 10.0)  # avant la période
        self.add(50, 21.0)
        self.add(20, 23.0)
        self.add(-5, 40.0)  # après la période (horloge capteur en avance)
        start = (self.now - timedelta(hours=1)).isoformat()
        end = self.now.isoformat()

        response = self.get(start=start, end=end)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["statistics"]["count"], 2)
        self.assertEqual(payload["statistics"]["minimum"], 21.0)
        self.assertEqual(payload["statistics"]["maximum"], 23.0)
        self.assertEqual(payload["bucket_minutes"], 1)
        self.assertEqual(payload["unit"], "°C")
        self.assertEqual(payload["timezone"], "America/Toronto")
        self.assertEqual(datetime.fromisoformat(payload["start"]), datetime.fromisoformat(start))

    def test_explicit_bucket_aggregates_points(self):
        for minutes_ago, value in [(55, 20.0), (50, 22.0), (25, 24.0)]:
            self.add(minutes_ago, value)
        start = (self.now - timedelta(hours=1)).isoformat()

        payload = self.get(start=start, end=self.now.isoformat(), bucket_minutes=30).json()

        self.assertEqual(payload["bucket_minutes"], 30)
        self.assertEqual(sum(point["count"] for point in payload["points"]), 3)
        self.assertLessEqual(len(payload["points"]), 3)

    def test_long_period_uses_coarser_automatic_bucket(self):
        start = (self.now - timedelta(days=30)).isoformat()
        payload = self.get(start=start, end=self.now.isoformat()).json()
        self.assertGreaterEqual(payload["bucket_minutes"], 60)

    def test_naive_datetimes_use_server_timezone(self):
        local_now = timezone.localtime(self.now).replace(tzinfo=None)
        start = (local_now - timedelta(hours=1)).isoformat()
        self.add(30, 22.0)
        payload = self.get(start=start, end=local_now.isoformat()).json()
        self.assertEqual(payload["statistics"]["count"], 1)

    def test_validation_errors_are_explicit(self):
        end = self.now.isoformat()
        cases = [
            ({"start": end}, None),
            ({"start": "hier", "end": end}, "start"),
            ({"start": end, "end": (self.now - timedelta(hours=1)).isoformat()}, "end"),
            ({"start": (self.now - timedelta(days=60)).isoformat(), "end": end}, "end"),
            ({"start": (self.now - timedelta(hours=1)).isoformat(), "end": end, "bucket_minutes": 7}, "bucket_minutes"),
            ({"start": (self.now - timedelta(days=30)).isoformat(), "end": end, "bucket_minutes": 1}, "bucket_minutes"),
            (
                {"start": (self.now + timedelta(hours=1)).isoformat(), "end": (self.now + timedelta(hours=2)).isoformat()},
                "start",
            ),
        ]
        for params, field in cases:
            with self.subTest(params=params):
                response = self.get(**params)
                self.assertEqual(response.status_code, 400)
                body = response.json()
                self.assertIn("detail", body)
                if field:
                    self.assertIn(field, body["errors"])

    def test_unknown_metric_and_zone(self):
        response = self.client.get("/api/zones/bureau/history/?type=pression")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Type de mesure invalide.", "errors": {"type": ["Type de mesure inconnu."]}})
        self.assertEqual(self.client.get("/api/zones/inconnue/history/").status_code, 404)

    @override_settings(HISTORY_MAX_RANGE_DAYS=2)
    def test_range_limit_is_configurable(self):
        start = (self.now - timedelta(days=3)).isoformat()
        response = self.get(start=start, end=self.now.isoformat())
        self.assertEqual(response.status_code, 400)
        self.assertIn("2 jours", response.json()["detail"])
