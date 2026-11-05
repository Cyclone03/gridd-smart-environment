from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from modules.comfort.domain.comfort_assessor import ComfortAssessor
from modules.comfort.domain.comfort_defaults import ComfortDefaults
from modules.comfort.domain.comfort_history_aggregator import ComfortHistoryAggregator


class ComfortAssessorTests(SimpleTestCase):
    def setUp(self):
        self.assessor = ComfortAssessor()
        self.profile = ComfortDefaults.OCCUPIED  # 20–24 °C ± 2, 30–60 % ± 10

    def assess(self, temperature, humidity):
        return self.assessor.assess(self.profile, temperature, humidity)

    def test_levels_and_statuses(self):
        comfortable = self.assess(22, 45)
        self.assertEqual((comfortable.level, comfortable.score), ("comfortable", 100.0))

        warm = self.assess(25, 45)
        self.assertEqual((warm.level, warm.temperature_status, warm.humidity_status), ("acceptable", "warm", "ok"))

        cold = self.assess(17, 45)
        self.assertEqual((cold.level, cold.temperature_status), ("uncomfortable", "too_cold"))

        dry = self.assess(22, 15)
        self.assertEqual((dry.level, dry.humidity_status), ("uncomfortable", "too_dry"))

    def test_score_is_weighted_and_decreases_with_distance(self):
        # Température à mi-tolérance (75) et humidité idéale (100) : 0,7 × 75 + 0,3 × 100.
        self.assertEqual(self.assess(25, 45).score, 82.5)
        self.assertEqual(self.assess(28, 45).score, 30.0)  # 0 pour la température à 2 × tolérance
        self.assertGreater(self.assess(24.5, 45).score, self.assess(25.5, 45).score)

    def test_missing_factor(self):
        only_temperature = self.assess(22, None)
        self.assertEqual((only_temperature.level, only_temperature.humidity_status), ("comfortable", "unknown"))
        self.assertEqual(only_temperature.score, 100.0)
        nothing = self.assess(None, None)
        self.assertEqual((nothing.level, nothing.score), ("unknown", None))

    def test_server_room_has_its_own_defaults(self):
        self.assertEqual(ComfortDefaults.for_zone_type("server_room").temperature_max, 27)
        self.assertEqual(ComfortDefaults.for_zone_type("office"), ComfortDefaults.OCCUPIED)


class ComfortHistoryAggregatorTests(SimpleTestCase):
    def test_points_and_summary(self):
        tz = timezone.get_current_timezone()
        start = timezone.make_aware(timezone.datetime(2026, 11, 4, 9, 0), tz)
        rows = [
            {"assessed_at": start, "score": 100, "level": "comfortable", "temperature": 22, "humidity": 40},
            {
                "assessed_at": start + timedelta(minutes=5),
                "score": 80,
                "level": "acceptable",
                "temperature": 25,
                "humidity": 40,
            },
            {
                "assessed_at": start + timedelta(hours=1),
                "score": 0,
                "level": "uncomfortable",
                "temperature": 30,
                "humidity": None,
            },
            {"assessed_at": start + timedelta(hours=1), "score": None, "level": "unknown", "temperature": None, "humidity": None},
        ]
        points, summary = ComfortHistoryAggregator().aggregate(rows, 60, tz)
        self.assertEqual(len(points), 2)
        self.assertEqual((points[0]["score"], points[0]["comfortable"], points[0]["acceptable"]), (90.0, 1, 1))
        self.assertIsNone(points[1]["humidity"])
        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["average_score"], 60.0)
        self.assertEqual(summary["uncomfortable_ratio"], 0.333)
