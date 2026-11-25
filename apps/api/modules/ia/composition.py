"""Racine de composition du module IA : assemble le cœur avec les adaptateurs
choisis par les réglages ``AI_*`` (voir README.md)."""

from pathlib import Path

from django.conf import settings

from modules.ia.adapters.http.gridd_api_observation_source import GriddApiObservationSource
from modules.ia.adapters.http.open_meteo_weather_source import OpenMeteoWeatherSource
from modules.ia.adapters.inference.keras_artifact_loaders import load_keras_model, load_scaler
from modules.ia.adapters.messaging.event_bus_prediction_publisher import EventBusPredictionPublisher
from modules.ia.adapters.persistence.database_observation_source import DatabaseObservationSource
from modules.ia.adapters.persistence.file_heartbeat import FileHeartbeat
from modules.ia.adapters.persistence.sqlite_prediction_ledger import SQLitePredictionLedger
from modules.ia.core.domain.scheduler_settings import SchedulerSettings
from modules.ia.core.inference.artifact_registry import ArtifactRegistry
from modules.ia.core.inference.scaler_approval import parse_approved_scaler_digests
from modules.ia.core.services.data_collection_service import DataCollectionService
from modules.ia.core.services.prediction_cycle import PredictionCycle
from modules.ia.core.services.prediction_scheduler import PredictionScheduler
from shared.messaging import Messaging

OBSERVATION_SOURCES = ("database", "api")


def observation_source():
    """``AI_OBSERVATION_SOURCE`` : ``database`` (lecture directe, par défaut)
    ou ``api`` (API REST GRIDD à ``GRIDD_API_BASE_URL``)."""
    if settings.AI_OBSERVATION_SOURCE == "api":
        return GriddApiObservationSource(settings.GRIDD_API_BASE_URL, timeout_seconds=settings.AI_HTTP_TIMEOUT_SECONDS)
    if settings.AI_OBSERVATION_SOURCE == "database":
        return DatabaseObservationSource()
    raise ValueError(f"AI_OBSERVATION_SOURCE must be one of {OBSERVATION_SOURCES}.")


def weather_source() -> OpenMeteoWeatherSource:
    if settings.OPEN_METEO_LATITUDE is None or settings.OPEN_METEO_LONGITUDE is None:
        raise ValueError("OPEN_METEO_LATITUDE and OPEN_METEO_LONGITUDE are required by the IA module.")
    return OpenMeteoWeatherSource(
        settings.OPEN_METEO_LATITUDE,
        settings.OPEN_METEO_LONGITUDE,
        timeout_seconds=settings.AI_HTTP_TIMEOUT_SECONDS,
    )


def data_collection_service() -> DataCollectionService:
    return DataCollectionService(weather=weather_source(), observations=observation_source())


def prediction_publisher() -> EventBusPredictionPublisher:
    return EventBusPredictionPublisher(Messaging.current().publisher())


def prediction_cycle() -> PredictionCycle:
    return PredictionCycle(
        registry=ArtifactRegistry(Path(settings.AI_ARTIFACT_MANIFEST_PATH)),
        approved_scaler_sha256=parse_approved_scaler_digests(settings.AI_APPROVED_SCALER_SHA256),
        isolated_environment=settings.AI_ISOLATED_ENVIRONMENT,
        model_loader=load_keras_model,
        scaler_loader=load_scaler,
        collection=data_collection_service(),
        publisher=prediction_publisher(),
        ledger_factory=lambda: SQLitePredictionLedger(settings.AI_PREDICTION_LEDGER_PATH),
    )


def scheduler_settings() -> SchedulerSettings:
    return SchedulerSettings(
        interval_seconds=settings.AI_PREDICTION_INTERVAL_SECONDS,
        heartbeat_interval_seconds=settings.AI_PREDICTION_HEARTBEAT_INTERVAL_SECONDS,
        heartbeat_max_age_seconds=settings.AI_PREDICTION_HEARTBEAT_MAX_AGE_SECONDS,
        heartbeat_path=Path(settings.AI_PREDICTION_HEARTBEAT_PATH),
        align_seconds=settings.AI_PREDICTION_ALIGN_SECONDS,
        align_offset_seconds=settings.AI_PREDICTION_ALIGN_OFFSET_SECONDS,
    )


def heartbeat() -> FileHeartbeat:
    return FileHeartbeat(settings.AI_PREDICTION_HEARTBEAT_PATH)


def prediction_scheduler(run_cycle) -> PredictionScheduler:
    return PredictionScheduler(run_cycle, scheduler_settings(), heartbeat())
