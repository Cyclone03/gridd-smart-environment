import logging
import os
from pathlib import Path

from .clients.gridd_api import GriddApiClient
from .clients.open_meteo import OpenMeteoClient
from .config import ServiceSettings
from .messaging.kafka_producer import KafkaPredictionProducer
from .models.artifacts import ArtifactRegistry
from .models.runtime import load_model_predictor
from .services.data_collection import DataCollectionService
from .services.orchestrator import PredictionOrchestrator
from .services.prediction_ledger import SQLitePredictionLedger

logger = logging.getLogger("ai_prediction_service")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    manifest_path = Path(
        os.environ.get(
            "AI_ARTIFACT_MANIFEST_PATH",
            str(Path(__file__).resolve().parents[2] / "artifacts" / "manifest.json"),
        )
    )
    registry = ArtifactRegistry(manifest_path)
    approved_scalers = {
        digest.strip()
        for digest in os.environ.get("AI_APPROVED_SCALER_SHA256", "").split(",")
        if digest.strip()
    }
    isolated_environment = os.environ.get("AI_ISOLATED_ENVIRONMENT", "").lower() == "true"
    settings = ServiceSettings.from_env()
    collection = DataCollectionService(
        weather=OpenMeteoClient(
            settings.open_meteo_latitude,
            settings.open_meteo_longitude,
            timeout_seconds=settings.http_timeout_seconds,
        ),
        observations=GriddApiClient(
            settings.gridd_api_base_url,
            timeout_seconds=settings.http_timeout_seconds,
        ),
    )
    producer = KafkaPredictionProducer.from_env()
    try:
        loaded_models = load_model_predictor(
            registry,
            approved_scaler_sha256=approved_scalers,
            isolated_environment=isolated_environment,
        )
    except RuntimeError as exc:
        logger.error(
            "No prediction models are available; publishing weather without inference: %s",
            exc,
        )
        producer.publish_weather_snapshot(collection.fetch_weather())
        return 1

    for failure in loaded_models.failures:
        logger.error(
            "Model bundle unavailable: zone=%s error=%s message=%s",
            failure.zone_code,
            failure.error_type,
            failure.message,
        )

    ledger_path = Path(
        os.environ.get(
            "AI_PREDICTION_LEDGER_PATH",
            str(Path.home() / ".gridd-ai-prediction" / "predictions.sqlite3"),
        )
    )
    result = PredictionOrchestrator(
        collection=collection,
        predictor=loaded_models.predictor,
        registry=registry,
        producer=producer,
        ledger=SQLitePredictionLedger(ledger_path),
    ).run_all()

    for prediction in result.successes:
        receipt = prediction.receipt
        logger.info(
            "Experimental prediction completed: zone=%s input_at=%s target_at=%s "
            "temperature_c=%.2f humidity_percent=%.2f model=%s topic=%s partition=%s offset=%s",
            prediction.zone_code,
            prediction.input_at.isoformat(),
            prediction.target_at.isoformat(),
            prediction.predicted_temperature_c,
            prediction.predicted_humidity_percent,
            prediction.model_version,
            receipt.topic,
            receipt.partition,
            receipt.offset,
        )
    for failure in result.failures:
        logger.error(
            "Prediction not published: zone=%s error=%s message=%s",
            failure.zone_code,
            failure.error_type,
            failure.message,
        )
    for zone_code in result.skipped:
        logger.info("Prediction already handled for unchanged input: zone=%s", zone_code)
    return 0 if not result.failures and not loaded_models.failures else 1
