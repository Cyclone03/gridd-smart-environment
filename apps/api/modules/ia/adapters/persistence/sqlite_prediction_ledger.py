import math
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from modules.ia.core.domain.pending_prediction import PendingPrediction
from modules.ia.core.domain.prediction_claim import PredictionClaim
from modules.ia.core.errors import PredictionLedgerError


class SQLitePredictionLedger:
    """Persists publication state so restarts can skip or replay the same event.

    Adaptateur SQLite du port ``PredictionLedger`` (fichier local, volume persistant).
    """

    def __init__(self, path: str | Path, *, lease_seconds: float = 300):
        if (
            isinstance(lease_seconds, bool)
            or not math.isfinite(lease_seconds)
            or lease_seconds <= 0
        ):
            raise ValueError("lease_seconds must be a positive finite number.")
        if not str(path).strip():
            raise ValueError("A prediction ledger path is required.")
        self._path = Path(path)
        self._lease_seconds = float(lease_seconds)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS prediction_runs (
                    zone_code TEXT NOT NULL,
                    input_at TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('computing', 'pending', 'published')),
                    lease_token TEXT,
                    lease_until REAL NOT NULL,
                    generated_at TEXT,
                    target_at TEXT,
                    predicted_temperature_c REAL,
                    predicted_humidity_percent REAL,
                    model_version TEXT,
                    prediction_mode TEXT,
                    PRIMARY KEY (zone_code, input_at)
                )
                """
            )

    def claim(self, zone_code: str, input_at: datetime) -> PredictionClaim | None:
        normalized_input = _utc_iso(input_at, "input_at")
        now = time.time()
        token = str(uuid4())
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT * FROM prediction_runs WHERE zone_code = ? AND input_at = ?",
                    (zone_code, normalized_input),
                ).fetchone()
                if row is not None and row["status"] == "published":
                    connection.commit()
                    return None
                if row is not None and row["lease_until"] > now:
                    connection.commit()
                    return None

                if row is None:
                    event_id = _event_id(zone_code, normalized_input)
                    connection.execute(
                        """
                        INSERT INTO prediction_runs
                            (zone_code, input_at, event_id, status, lease_token, lease_until)
                        VALUES (?, ?, ?, 'computing', ?, ?)
                        """,
                        (
                            zone_code,
                            normalized_input,
                            event_id,
                            token,
                            now + self._lease_seconds,
                        ),
                    )
                    pending = None
                else:
                    event_id = row["event_id"]
                    connection.execute(
                        """
                        UPDATE prediction_runs
                        SET lease_token = ?, lease_until = ?
                        WHERE zone_code = ? AND input_at = ?
                        """,
                        (
                            token,
                            now + self._lease_seconds,
                            zone_code,
                            normalized_input,
                        ),
                    )
                    pending = _pending_from_row(row) if row["status"] == "pending" else None
                connection.commit()
            except Exception:
                connection.rollback()
                raise

        return PredictionClaim(
            zone_code=zone_code,
            input_at=input_at.astimezone(timezone.utc),
            event_id=event_id,
            lease_token=token,
            pending=pending,
        )

    def store_pending(
        self,
        claim: PredictionClaim,
        *,
        generated_at: datetime,
        target_at: datetime,
        predicted_temperature_c: float,
        predicted_humidity_percent: float,
        model_version: str,
        prediction_mode: str,
    ) -> None:
        values = (
            _utc_iso(generated_at, "generated_at"),
            _utc_iso(target_at, "target_at"),
            predicted_temperature_c,
            predicted_humidity_percent,
            model_version,
            prediction_mode,
            time.time() + self._lease_seconds,
            claim.zone_code,
            _utc_iso(claim.input_at, "input_at"),
            claim.lease_token,
        )
        self._update_claim(
            """
            UPDATE prediction_runs
            SET status = 'pending', generated_at = ?, target_at = ?,
                predicted_temperature_c = ?, predicted_humidity_percent = ?,
                model_version = ?, prediction_mode = ?, lease_until = ?
            WHERE zone_code = ? AND input_at = ? AND lease_token = ? AND status = 'computing'
            """,
            values,
            "Could not store a pending climate prediction.",
        )

    def mark_published(self, claim: PredictionClaim) -> None:
        self._update_claim(
            """
            UPDATE prediction_runs
            SET status = 'published', lease_token = NULL, lease_until = 0
            WHERE zone_code = ? AND input_at = ? AND lease_token = ? AND status = 'pending'
            """,
            (
                claim.zone_code,
                _utc_iso(claim.input_at, "input_at"),
                claim.lease_token,
            ),
            "Could not mark the climate prediction as published.",
        )

    def release(self, claim: PredictionClaim) -> None:
        self._update_claim(
            """
            UPDATE prediction_runs
            SET lease_token = NULL, lease_until = 0
            WHERE zone_code = ? AND input_at = ? AND lease_token = ?
            """,
            (
                claim.zone_code,
                _utc_iso(claim.input_at, "input_at"),
                claim.lease_token,
            ),
            "Could not release the climate prediction claim.",
            require_match=False,
        )

    def _update_claim(self, statement, values, error, *, require_match=True) -> None:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                cursor = connection.execute(statement, values)
                if require_match and cursor.rowcount != 1:
                    raise PredictionLedgerError(error)
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def _connect(self):
        connection = sqlite3.connect(self._path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection


def _event_id(zone_code: str, input_at: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"gridd.climate_prediction:{zone_code}:{input_at}"))


def _pending_from_row(row: sqlite3.Row) -> PendingPrediction:
    required = (
        row["generated_at"],
        row["target_at"],
        row["predicted_temperature_c"],
        row["predicted_humidity_percent"],
        row["model_version"],
        row["prediction_mode"],
    )
    if any(value is None for value in required):
        raise PredictionLedgerError("Pending prediction record is incomplete.")
    return PendingPrediction(
        generated_at=datetime.fromisoformat(row["generated_at"]),
        target_at=datetime.fromisoformat(row["target_at"]),
        predicted_temperature_c=row["predicted_temperature_c"],
        predicted_humidity_percent=row["predicted_humidity_percent"],
        model_version=row["model_version"],
        prediction_mode=row["prediction_mode"],
    )


def _utc_iso(value: datetime, label: str) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware timestamp.")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
