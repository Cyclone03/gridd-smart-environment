from datetime import datetime, timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from modules.history.domain.history_statistics import HistoryStatistics
from shared.periods import PeriodParamError, PeriodParser, TimeBucket


class HistoryDomainTests(SimpleTestCase):
    def setUp(self):
        self.parser = PeriodParser(max_range_days=31, target_points=400, max_points=3000)

    def test_choose_bucket_targets_point_count(self):
        choose = PeriodParser.choose_bucket_minutes
        self.assertEqual(choose(timedelta(minutes=15), 400), 1)
        self.assertEqual(choose(timedelta(days=1), 400), 5)
        self.assertEqual(choose(timedelta(days=7), 400), 30)
        self.assertEqual(choose(timedelta(days=31), 400), 180)

    def test_daily_buckets_are_aligned_on_local_midnight(self):
        tz = timezone.get_current_timezone()
        moment = timezone.make_aware(datetime(2026, 10, 27, 23, 30), tz)
        start = TimeBucket.start_of(moment, 1440, tz)
        self.assertEqual((start.hour, start.minute, start.day), (0, 0, 27))

    def test_legacy_parameters_keep_their_buckets(self):
        self.assertEqual(self.parser.parse({"hours": "6"}).bucket_minutes, 5)
        self.assertEqual(self.parser.parse({"hours": "168"}).bucket_minutes, 60)
        self.assertEqual(self.parser.parse({"date": "2026-10-20"}).bucket_minutes, 15)
        with self.assertRaises(PeriodParamError):
            self.parser.parse({"hours": "5"})

    def test_trend(self):
        point = lambda average: {"average": average}  # noqa: E731
        self.assertEqual(HistoryStatistics.trend([point(20), point(21)], 0.2), "rising")
        self.assertEqual(HistoryStatistics.trend([point(21), point(20.9)], 0.2), "stable")
        self.assertEqual(HistoryStatistics.trend([point(21)], 0.2), "stable")
