import logging
from collections.abc import Callable, Set
from pathlib import Path

from modules.ia.core.errors import ArtifactTrustError

from .artifact_loader import ArtifactLoader
from .artifact_registry import ArtifactRegistry
from .model_load_failure import ModelLoadFailure
from .model_load_result import ModelLoadResult
from .model_predictor import ModelPredictor

logger = logging.getLogger(__name__)


def load_model_predictor(
    registry: ArtifactRegistry,
    *,
    approved_scaler_sha256: Set[str],
    isolated_environment: bool,
    model_loader: Callable[[Path], object],
    scaler_loader: Callable[[Path], object],
) -> ModelLoadResult:
    """Load verified zone bundles while preserving usable zones after a local failure.

    ``model_loader`` and ``scaler_loader`` are injected (see
    ``modules.ia.adapters.inference.keras_artifact_loaders``): the core never
    imports TensorFlow or joblib.
    """

    loader = ArtifactLoader(model_loader=model_loader, scaler_loader=scaler_loader)
    bundles = {}
    failures = []
    for zone_code in registry.zone_codes():
        spec = registry.for_zone(zone_code)
        try:
            bundles[zone_code] = loader.load(
                spec,
                approved_scaler_sha256=approved_scaler_sha256,
                isolated_environment=isolated_environment,
            )
        except ArtifactTrustError as exc:
            # Configuration attendue tant que l'approbation n'est pas faite :
            # un message clair suffit, sans trace de pile répétée par zone.
            logger.error("Model artifacts not trusted for zone %s: %s", zone_code, exc)
            failures.append(ModelLoadFailure(zone_code, type(exc).__name__, str(exc)))
        except ImportError as exc:
            # Dépendances d'inférence absentes (image API) : pas de trace de pile.
            logger.error("Inference dependencies are missing for zone %s: %s", zone_code, exc)
            failures.append(ModelLoadFailure(zone_code, type(exc).__name__, str(exc)))
        except Exception as exc:
            logger.exception("Model artifacts could not be loaded for zone %s.", zone_code)
            failures.append(ModelLoadFailure(zone_code, type(exc).__name__, str(exc)))

    if not bundles:
        errors = "; ".join(f"{failure.zone_code}: {failure.message}" for failure in failures)
        raise RuntimeError(f"No zone model bundle could be loaded. {errors}")
    return ModelLoadResult(ModelPredictor(bundles), tuple(failures))
