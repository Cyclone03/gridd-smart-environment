import logging
from collections.abc import Callable, Set
from dataclasses import dataclass
from pathlib import Path

from .artifacts import ArtifactLoader, ArtifactRegistry, ArtifactTrustError
from .predictor import ModelPredictor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelLoadFailure:
    zone_code: str
    error_type: str
    message: str


@dataclass(frozen=True)
class ModelLoadResult:
    predictor: ModelPredictor
    failures: tuple[ModelLoadFailure, ...]


def load_model_predictor(
    registry: ArtifactRegistry,
    *,
    approved_scaler_sha256: Set[str],
    isolated_environment: bool,
    model_loader: Callable[[Path], object] | None = None,
    scaler_loader: Callable[[Path], object] | None = None,
) -> ModelLoadResult:
    """Load verified zone bundles while preserving usable zones after a local failure."""
    if model_loader is None or scaler_loader is None:
        try:
            import joblib
            from tensorflow.keras.models import load_model
        except ImportError as exc:
            raise RuntimeError(
                "Model loading requires the service 'inference' dependencies."
            ) from exc
        model_loader = model_loader or (lambda path: load_model(path, compile=False))
        scaler_loader = scaler_loader or joblib.load

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
        except Exception as exc:
            logger.exception("Model artifacts could not be loaded for zone %s.", zone_code)
            failures.append(ModelLoadFailure(zone_code, type(exc).__name__, str(exc)))

    if not bundles:
        errors = "; ".join(f"{failure.zone_code}: {failure.message}" for failure in failures)
        raise RuntimeError(f"No zone model bundle could be loaded. {errors}")
    return ModelLoadResult(ModelPredictor(bundles), tuple(failures))
