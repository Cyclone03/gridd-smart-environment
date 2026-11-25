"""Racine de composition du module Observations."""

from modules.observations.adapters.persistence.climate_prediction_repository import ClimatePredictionRepository
from modules.observations.adapters.persistence.observation_repository import ObservationRepository
from modules.observations.adapters.persistence.sensor_repository import SensorRepository
from modules.observations.adapters.persistence.weather_snapshot_repository import WeatherSnapshotRepository
from modules.observations.adapters.persistence.zone_repository import ZoneRepository
from modules.observations.core.services.observation_service import ObservationService
from modules.observations.core.services.sensor_service import SensorService
from modules.observations.core.services.weather_snapshot_service import WeatherSnapshotService
from modules.observations.core.services.zone_service import ZoneService


def observation_service() -> ObservationService:
    return ObservationService(
        observations=ObservationRepository(),
        zones=ZoneRepository(),
        climate_predictions=ClimatePredictionRepository(),
    )


def sensor_service() -> SensorService:
    return SensorService(SensorRepository())


def zone_service() -> ZoneService:
    return ZoneService(ZoneRepository())


def weather_snapshot_service() -> WeatherSnapshotService:
    return WeatherSnapshotService(WeatherSnapshotRepository())
