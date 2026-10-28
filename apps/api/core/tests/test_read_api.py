from datetime import datetime, timedelta

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from core.history import bucket_start, choose_bucket_minutes, parse_period, HistoryParamError
from core.models import Alert, Observation, Sensor, Zone


class LegacyHistoryApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.zone = Zone.objects.create(name="Bureau", code="bureau", zone_type="office")
        self.sensor = Sensor.objects.create(
            node_id="bureau-temperature",
            sensor_type="temperature",
            zone=self.zone,
            unit="°C",
        )

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

        response = self.client.get(
            "/api/zones/bureau/history/?type=temperature&hours=24"
        )

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
        day_start = timezone.make_aware(
            datetime.combine(selected_day, datetime.min.time()),
            local_timezone,
        )
        Observation.objects.create(
            sensor=self.sensor,
            zone=self.zone,
            type="temperature",
            value=22.0,
            unit="°C",
            observed_at=day_start + timedelta(hours=10),
        )
        Observation.objects.create(
            sensor=self.sensor,
            zone=self.zone,
            type="temperature",
            value=99.0,
            unit="°C",
            observed_at=day_start - timedelta(minutes=1),
        )

        response = self.client.get(
            f"/api/zones/bureau/history/?type=temperature&date={selected_day.isoformat()}"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["date"], selected_day.isoformat())
        self.assertEqual(payload["statistics"]["count"], 1)
        self.assertEqual(payload["statistics"]["average"], 22.0)


class PeriodHistoryApiTests(TestCase):
    """Contrat start/end/bucket_minutes ajouté pour les périodes configurables."""

    def setUp(self):
        self.client = Client()
        self.zone = Zone.objects.create(name="Bureau", code="bureau", zone_type="office")
        self.sensor = Sensor.objects.create(
            node_id="bureau-temperature", sensor_type="temperature", zone=self.zone, unit="C"
        )
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
        self.assertEqual(
            datetime.fromisoformat(payload["start"]),
            datetime.fromisoformat(start),
        )

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
            ({"start": (self.now + timedelta(hours=1)).isoformat(), "end": (self.now + timedelta(hours=2)).isoformat()}, "start"),
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
        self.assertEqual(self.client.get("/api/zones/bureau/history/?type=pression").status_code, 400)
        self.assertEqual(self.client.get("/api/zones/inconnue/history/").status_code, 404)

    @override_settings(HISTORY_MAX_RANGE_DAYS=2)
    def test_range_limit_is_configurable(self):
        start = (self.now - timedelta(days=3)).isoformat()
        response = self.get(start=start, end=self.now.isoformat())
        self.assertEqual(response.status_code, 400)
        self.assertIn("2 jours", response.json()["detail"])


class HistoryHelpersTests(TestCase):
    def test_choose_bucket_targets_point_count(self):
        self.assertEqual(choose_bucket_minutes(timedelta(minutes=15), 400), 1)
        self.assertEqual(choose_bucket_minutes(timedelta(days=1), 400), 5)
        self.assertEqual(choose_bucket_minutes(timedelta(days=7), 400), 30)
        self.assertEqual(choose_bucket_minutes(timedelta(days=31), 400), 180)

    def test_daily_buckets_are_aligned_on_local_midnight(self):
        tz = timezone.get_current_timezone()
        moment = timezone.make_aware(datetime(2026, 10, 27, 23, 30), tz)
        start = bucket_start(moment, 1440, tz)
        self.assertEqual((start.hour, start.minute, start.day), (0, 0, 27))

    def test_legacy_parameters_keep_their_buckets(self):
        self.assertEqual(parse_period({"hours": "6"}).bucket_minutes, 5)
        self.assertEqual(parse_period({"hours": "168"}).bucket_minutes, 60)
        self.assertEqual(parse_period({"date": "2026-10-20"}).bucket_minutes, 15)
        with self.assertRaises(HistoryParamError):
            parse_period({"hours": "5"})


class LatestObservationsApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.office = Zone.objects.create(
            name="Bureau des professeurs",
            code="professors-office",
            zone_type="office",
        )
        self.room = Zone.objects.create(
            name="Salle de réunion",
            code="meeting-room",
            zone_type="meeting_room",
        )
        self.temperature_sensor = Sensor.objects.create(
            node_id="office-temperature",
            sensor_type="temperature",
            zone=self.office,
            unit="°C",
        )
        self.humidity_sensor = Sensor.objects.create(
            node_id="room-humidity",
            sensor_type="humidity",
            zone=self.room,
            unit="%",
        )
        self.sound_sensor = Sensor.objects.create(
            node_id="office-sound",
            sensor_type="sound_level",
            zone=self.office,
            unit="dBA",
        )

    def test_latest_keeps_infrequent_metrics_outside_global_feed_limit(self):
        old_time = timezone.now() - timedelta(hours=1)
        temperature = Observation.objects.create(
            sensor=self.temperature_sensor,
            zone=self.office,
            type="temperature",
            value=22.4,
            unit="°C",
            observed_at=old_time,
        )
        humidity = Observation.objects.create(
            sensor=self.humidity_sensor,
            zone=self.room,
            type="humidity",
            value=41.0,
            unit="%",
            observed_at=None,
            received_at=old_time,
        )
        Observation.objects.bulk_create([
            Observation(
                sensor=self.sound_sensor,
                zone=self.office,
                type="sound_level",
                value=45.0,
                unit="dBA",
                observed_at=timezone.now() + timedelta(seconds=index),
            )
            for index in range(1001)
        ])

        feed_ids = {item["id"] for item in self.client.get("/api/observations/").json()}
        self.assertNotIn(temperature.id, feed_ids)
        self.assertNotIn(humidity.id, feed_ids)

        response = self.client.get("/api/observations/latest/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        latest_by_key = {(item["zone"], item["type"]): item for item in payload}
        self.assertEqual(
            latest_by_key[(self.office.id, "temperature")]["value"],
            22.4,
        )
        self.assertEqual(
            latest_by_key[(self.room.id, "humidity")]["value"],
            41.0,
        )


class ZoneApiTests(TestCase):
    def test_zone_exposes_metrics_from_active_sensors(self):
        zone = Zone.objects.create(name="Salle", code="salle", zone_type="meeting_room")
        Sensor.objects.create(node_id="n1", sensor_type="humidity", zone=zone, unit="%")
        Sensor.objects.create(node_id="n1", sensor_type="temperature", zone=zone, unit="C")
        Sensor.objects.create(node_id="n2", sensor_type="sound_level", zone=zone, unit="dBA", active=False)

        payload = self.client.get("/api/zones/").json()

        self.assertEqual(payload[0]["metrics"], ["temperature", "humidity"])


class AlertEventsApiTests(TestCase):
    def setUp(self):
        self.zone = Zone.objects.create(name="Salle", code="salle")
        self.old = Alert.objects.create(
            zone=self.zone, code="X", message="ancienne", severity="warning", active=False,
            created_at=timezone.now() - timedelta(days=3), resolved_at=timezone.now(),
        )
        self.current = Alert.objects.create(zone=self.zone, code="Y", message="en cours", severity="critical")

    def test_filters(self):
        ids = lambda query: [item["id"] for item in self.client.get(f"/api/alerts/{query}").json()]
        self.assertEqual(ids("?active=true"), [self.current.id])
        self.assertEqual(ids("?severity=warning"), [self.old.id])
        since = (timezone.now() - timedelta(days=1)).isoformat()
        response = self.client.get("/api/alerts/", {"since": since})
        self.assertEqual([item["id"] for item in response.json()], [self.current.id])
        self.assertEqual(ids("?limit=1"), [self.current.id])

    def test_invalid_filter_is_rejected(self):
        response = self.client.get("/api/alerts/?since=hier")
        self.assertEqual(response.status_code, 400)
        self.assertIn("since", response.json()["errors"])


class HealthAndRoutingTests(TestCase):
    def test_health_reports_database(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"], "connected")

    def test_backend_no_longer_serves_the_interface(self):
        for path in ["/", "/spaces/", "/history/", "/alerts/", "/legacy/"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
