"""Exceptions du module IA (une par fichier)."""

from .artifact_error import ArtifactError
from .artifact_integrity_error import ArtifactIntegrityError
from .artifact_manifest_error import ArtifactManifestError
from .artifact_not_found_error import ArtifactNotFoundError
from .artifact_trust_error import ArtifactTrustError
from .collection_error import CollectionError
from .gridd_api_error import GriddApiError
from .http_request_error import HttpRequestError
from .incomplete_observations_error import IncompleteObservationsError
from .incomplete_weather_response import IncompleteWeatherResponse
from .invalid_gridd_response import InvalidGriddResponse
from .model_contract_error import ModelContractError
from .open_meteo_error import OpenMeteoError
from .prediction_input_error import PredictionInputError
from .prediction_ledger_error import PredictionLedgerError
from .prediction_publication_error import PredictionPublicationError
from .timestamp_format_error import TimestampFormatError
from .unknown_zone_artifacts_error import UnknownZoneArtifactsError
from .unknown_zone_error import UnknownZoneError

__all__ = [
    "ArtifactError",
    "ArtifactIntegrityError",
    "ArtifactManifestError",
    "ArtifactNotFoundError",
    "ArtifactTrustError",
    "CollectionError",
    "GriddApiError",
    "HttpRequestError",
    "IncompleteObservationsError",
    "IncompleteWeatherResponse",
    "InvalidGriddResponse",
    "ModelContractError",
    "OpenMeteoError",
    "PredictionInputError",
    "PredictionLedgerError",
    "PredictionPublicationError",
    "TimestampFormatError",
    "UnknownZoneArtifactsError",
    "UnknownZoneError",
]
