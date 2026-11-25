from dataclasses import dataclass

from .model_load_failure import ModelLoadFailure
from .model_predictor import ModelPredictor


@dataclass(frozen=True)
class ModelLoadResult:
    predictor: ModelPredictor
    failures: tuple[ModelLoadFailure, ...]
