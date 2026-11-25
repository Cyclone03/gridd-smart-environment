import logging
from collections.abc import Callable, Set
from pathlib import Path

from modules.ia.core.domain.weather_snapshot_event import WeatherSnapshotEvent
from modules.ia.core.inference.artifact_registry import ArtifactRegistry
from modules.ia.core.inference.model_loading import load_model_predictor

from .data_collection_service import DataCollectionService
from .prediction_orchestrator import PredictionOrchestrator

logger = logging.getLogger(__name__)


class PredictionCycle:
    """Un cycle complet : chargement vérifié des modèles, météo partagée puis
    une prédiction H+1 par zone.

    Sans aucun modèle utilisable (empreintes des scalers non approuvées,
    dépendances d'inférence absentes…), l'instantané météo est tout de même
    publié et le cycle se termine en erreur.

    ``model_loader`` / ``scaler_loader`` : fonctions de chargement injectées
    (TensorFlow et joblib dans l'image IA) ; ``ledger_factory`` crée le port
    ``PredictionLedger`` (appelé seulement si des modèles sont chargés).
    """

    def __init__(
        self,
        *,
        registry: ArtifactRegistry,
        approved_scaler_sha256: Set[str],
        isolated_environment: bool,
        model_loader: Callable[[Path], object],
        scaler_loader: Callable[[Path], object],
        collection: DataCollectionService,
        publisher,
        ledger_factory: Callable[[], object] | None = None,
    ):
        self._registry = registry
        self._approved_scaler_sha256 = approved_scaler_sha256
        self._isolated_environment = isolated_environment
        self._model_loader = model_loader
        self._scaler_loader = scaler_loader
        self._collection = collection
        self._publisher = publisher
        self._ledger_factory = ledger_factory

    def run(self, zone_code: str | None = None) -> int:
        """Retourne 0 si toutes les zones ont été traitées, 1 sinon."""
        if not self._approved_scaler_sha256:
            logger.error(
                "AI_APPROVED_SCALER_SHA256 is empty: no scaler can be loaded until the 12 scaler "
                "digests listed in the artifact manifest are reviewed and approved."
            )
        try:
            loaded_models = load_model_predictor(
                self._registry,
                approved_scaler_sha256=self._approved_scaler_sha256,
                isolated_environment=self._isolated_environment,
                model_loader=self._model_loader,
                scaler_loader=self._scaler_loader,
            )
        except RuntimeError as exc:
            logger.error("No prediction models are available; publishing weather without inference: %s", exc)
            self._publisher.publish_weather_snapshot(WeatherSnapshotEvent.create(snapshot=self._collection.fetch_weather()))
            return 1

        for failure in loaded_models.failures:
            logger.error(
                "Model bundle unavailable: zone=%s error=%s message=%s",
                failure.zone_code,
                failure.error_type,
                failure.message,
            )

        orchestrator = PredictionOrchestrator(
            collection=self._collection,
            predictor=loaded_models.predictor,
            registry=self._registry,
            producer=self._publisher,
            ledger=self._ledger_factory() if self._ledger_factory is not None else None,
        )
        if zone_code is not None:
            prediction = orchestrator.run_zone(zone_code)
            if prediction is None:
                logger.info("Prediction already handled for unchanged input: zone=%s", zone_code)
            else:
                self._log_success(prediction)
            return 0 if not loaded_models.failures else 1

        result = orchestrator.run_all()
        for prediction in result.successes:
            self._log_success(prediction)
        for failure in result.failures:
            logger.error(
                "Prediction not published: zone=%s error=%s message=%s",
                failure.zone_code,
                failure.error_type,
                failure.message,
            )
        for skipped_zone in result.skipped:
            logger.info("Prediction already handled for unchanged input: zone=%s", skipped_zone)
        return 0 if not result.failures and not loaded_models.failures else 1

    @staticmethod
    def _log_success(prediction):
        logger.info(
            "Experimental prediction completed: zone=%s input_at=%s target_at=%s "
            "temperature_c=%.2f humidity_percent=%.2f model=%s event_id=%s topic=%s",
            prediction.zone_code,
            prediction.input_at.isoformat(),
            prediction.target_at.isoformat(),
            prediction.predicted_temperature_c,
            prediction.predicted_humidity_percent,
            prediction.model_version,
            prediction.receipt.event_id,
            prediction.receipt.topic,
        )
