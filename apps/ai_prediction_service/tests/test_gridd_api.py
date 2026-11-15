import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from ai_prediction_service.clients.gridd_api import GriddApiClient
from ai_prediction_service.errors import (
    GriddApiError,
    HttpRequestError,
    IncompleteObservationsError,
    InvalidGriddResponse,
    UnknownZoneError,
)


ZONE_CODES = (
    "professors-office",
    "individual-work-cubicle-01",
    "individual-work-cubicle-02",
    "open-workspace",
    "meeting-room",
    "server-equipment-room",
)


def zones_payload():
    return [{"code": code, "active": True} for code in ZONE_CODES]


def observations_payload():
    entries = []
    for code in ZONE_CODES:
        entries.extend(
            [
                {
                    "zone_code": code,
                    "type": "temperature",
                    "value": 21.5,
                    "unit": "°C",
                    "observed_at": "2026-11-13T16:00:00-05:00",
                    "received_at": "2026-11-13T21:00:02Z",
                    "quality_status": "normal",
                },
                {
                    "zone_code": code,
                    "type": "humidity",
                    "value": 42.0,
                    "unit": "%",
                    "observed_at": None,
                    "received_at": "2026-11-13T21:00:03+00:00",
                    "quality_status": "normal",
                },
            ]
        )
    return entries


class GriddApiClientTests(unittest.TestCase):
    def setUp(self):
        self.transport = Mock(side_effect=[zones_payload(), observations_payload()])
        self.client = GriddApiClient("http://gridd.test/", transport=self.transport)

    def test_fetches_latest_temperature_and_humidity_for_active_zone_codes(self):
        result = self.client.fetch_latest()

        self.assertEqual(tuple(result), ZONE_CODES)
        self.assertEqual(result["meeting-room"].temperature.value, 21.5)
        self.assertEqual(
            result["meeting-room"].temperature.observed_at,
            datetime(2026, 11, 13, 21, 0, tzinfo=timezone.utc),
        )
        self.assertIsNone(result["meeting-room"].humidity.observed_at)
        self.assertEqual(
            result["meeting-room"].humidity.effective_at,
            datetime(2026, 11, 13, 21, 0, 3, tzinfo=timezone.utc),
        )
        self.assertEqual(
            [call.args[0] for call in self.transport.call_args_list],
            ["http://gridd.test/api/zones/", "http://gridd.test/api/observations/latest/"],
        )

    def test_unknown_zone_is_rejected_without_mapping_to_model_ids(self):
        with self.assertRaises(UnknownZoneError):
            self.client.fetch_latest(("unknown-zone",))
        self.assertEqual(self.transport.call_count, 1)

    def test_missing_metric_for_a_zone_is_rejected(self):
        incomplete = observations_payload()
        incomplete = [
            item for item in incomplete
            if not (item["zone_code"] == "meeting-room" and item["type"] == "humidity")
        ]
        self.transport.side_effect = [zones_payload(), incomplete]

        with self.assertRaises(IncompleteObservationsError):
            self.client.fetch_latest()

    def test_empty_active_zone_list_is_rejected(self):
        self.transport.side_effect = [[]]

        with self.assertRaises(IncompleteObservationsError):
            self.client.fetch_latest()

    def test_connection_failure_is_reported(self):
        self.transport.side_effect = HttpRequestError("connection refused")

        with self.assertRaises(GriddApiError):
            self.client.fetch_latest()

    def test_naive_timestamp_is_rejected(self):
        entries = observations_payload()
        entries[0]["observed_at"] = "2026-11-13T16:00:00"
        self.transport.side_effect = [zones_payload(), entries]

        with self.assertRaises(InvalidGriddResponse):
            self.client.fetch_latest()

    def test_zone_code_filter_collects_only_requested_codes(self):
        result = self.client.fetch_latest(("meeting-room",))

        self.assertEqual(tuple(result), ("meeting-room",))
        self.assertEqual(self.transport.call_count, 2)

    def test_empty_zone_code_filter_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            self.client.fetch_latest(())


if __name__ == "__main__":
    unittest.main()
