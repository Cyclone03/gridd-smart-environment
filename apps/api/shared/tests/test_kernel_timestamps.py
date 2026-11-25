from datetime import timedelta, timezone

from django.test import SimpleTestCase
from django.utils.dateparse import parse_datetime as django_parse_datetime

from shared.kernel.timestamps import is_utc, parse_datetime


class KernelTimestampsTests(SimpleTestCase):
    """Le noyau pur se comporte comme ``django.utils.dateparse`` pour les
    formats utilisés par l'API et les événements."""

    def test_matches_django_for_supported_formats(self):
        for value in (
            "2026-10-27T08:00:00-04:00",
            "2026-10-27T12:00:00+00:00",
            "2026-10-27T12:00:00Z",
            "2026-10-27 08:00",
            "2026-10-27T08:00:00.123456",
        ):
            with self.subTest(value=value):
                self.assertEqual(parse_datetime(value), django_parse_datetime(value))

    def test_rejects_dates_without_time_and_garbage(self):
        for value in ("2026-10-27", "hier", "", None, 42):
            with self.subTest(value=value):
                self.assertIsNone(parse_datetime(value))

    def test_is_utc(self):
        self.assertTrue(is_utc(parse_datetime("2026-10-27T12:00:00+00:00")))
        self.assertFalse(is_utc(parse_datetime("2026-10-27T08:00:00-04:00")))
        self.assertFalse(is_utc(parse_datetime("2026-10-27T08:00:00")))
        self.assertEqual(parse_datetime("2026-10-27T12:00:00Z").utcoffset(), timedelta(0))
        self.assertEqual(parse_datetime("2026-10-27T12:00:00Z").tzinfo, timezone.utc)
