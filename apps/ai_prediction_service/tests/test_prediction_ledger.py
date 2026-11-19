import unittest
from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory

from ai_prediction_service.services.prediction_ledger import SQLitePredictionLedger


class SQLitePredictionLedgerTests(unittest.TestCase):
    def setUp(self):
        self.input_at = datetime(2026, 11, 15, 19, 0, tzinfo=timezone.utc)

    def test_published_input_is_deduplicated_after_reopening_the_ledger(self):
        with TemporaryDirectory() as temp_dir:
            path = f"{temp_dir}/predictions.sqlite3"
            ledger = SQLitePredictionLedger(path)
            claim = ledger.claim("open-workspace", self.input_at)
            self.assertIsNotNone(claim)
            ledger.store_pending(
                claim,
                generated_at=self.input_at + timedelta(seconds=1),
                target_at=self.input_at + timedelta(hours=1),
                predicted_temperature_c=23.5,
                predicted_humidity_percent=45.0,
                model_version="modelZone1:sha256:test",
                prediction_mode="experimental",
            )
            ledger.mark_published(claim)

            reopened = SQLitePredictionLedger(path)
            self.assertIsNone(reopened.claim("open-workspace", self.input_at))

    def test_pending_event_is_replayed_with_the_same_identity_and_values(self):
        with TemporaryDirectory() as temp_dir:
            path = f"{temp_dir}/predictions.sqlite3"
            ledger = SQLitePredictionLedger(path)
            first_claim = ledger.claim("open-workspace", self.input_at)
            generated_at = self.input_at + timedelta(seconds=1)
            target_at = self.input_at + timedelta(hours=1)
            ledger.store_pending(
                first_claim,
                generated_at=generated_at,
                target_at=target_at,
                predicted_temperature_c=23.5,
                predicted_humidity_percent=45.0,
                model_version="modelZone1:sha256:test",
                prediction_mode="experimental",
            )
            ledger.release(first_claim)

            restarted = SQLitePredictionLedger(path)
            retry_claim = restarted.claim("open-workspace", self.input_at)

        self.assertIsNotNone(retry_claim)
        self.assertEqual(retry_claim.event_id, first_claim.event_id)
        self.assertEqual(retry_claim.pending.generated_at, generated_at)
        self.assertEqual(retry_claim.pending.target_at, target_at)
        self.assertEqual(retry_claim.pending.predicted_temperature_c, 23.5)
        self.assertEqual(retry_claim.pending.prediction_mode, "experimental")

    def test_a_live_claim_prevents_a_second_worker_from_publishing(self):
        with TemporaryDirectory() as temp_dir:
            path = f"{temp_dir}/predictions.sqlite3"
            first = SQLitePredictionLedger(path)
            second = SQLitePredictionLedger(path)

            claim = first.claim("open-workspace", self.input_at)
            duplicate = second.claim("open-workspace", self.input_at)

        self.assertIsNotNone(claim)
        self.assertIsNone(duplicate)


if __name__ == "__main__":
    unittest.main()
