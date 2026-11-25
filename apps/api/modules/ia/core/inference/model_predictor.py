import math
from collections.abc import Mapping, Sequence
from numbers import Real

from modules.ia.core.domain.zones import ZONE_MODEL_MAPPING
from modules.ia.core.errors import ModelContractError, UnknownZoneArtifactsError

from .contract import ordered_input_values, validate_model_and_scalers
from .loaded_model_bundle import LoadedModelBundle


class ModelPredictor:
    """Runs a loaded model bundle using the confirmed named feature contract."""

    def __init__(self, bundles: Mapping[str, LoadedModelBundle]):
        if not bundles:
            raise ModelContractError("At least one loaded model bundle is required.")
        for zone_code, bundle in bundles.items():
            expected_code = ZONE_MODEL_MAPPING.get(bundle.spec.zone_number)
            if zone_code != bundle.spec.zone_code or zone_code != expected_code:
                raise ModelContractError(
                    f"Model zone {bundle.spec.zone_number} must map to {expected_code!r}."
                )
            validate_model_and_scalers(bundle.model, bundle.scaler_x, bundle.scaler_y)
        self._bundles = dict(bundles)

    def predict_one(self, zone_code: str, features: Mapping[str, Real]) -> tuple[float, float]:
        try:
            bundle = self._bundles[zone_code]
        except KeyError as exc:
            raise UnknownZoneArtifactsError(f"No loaded model bundle for zone {zone_code!r}.") from exc

        import numpy as np  # dépendance de l'inférence uniquement (image IA)

        row = list(ordered_input_values(features))
        scaled = _matrix(bundle.scaler_x.transform([row]), 1, 4, "scaled X")
        model_input = np.asarray(scaled, dtype=np.float32).reshape((1, 4, 1))
        predicted = _matrix(bundle.model.predict(model_input, verbose=0), 1, 2, "model output")
        values = _matrix(bundle.scaler_y.inverse_transform(predicted), 1, 2, "inverse-scaled Y")
        return values[0][0], values[0][1]


def _matrix(value: object, rows: int, columns: int, label: str) -> list[list[float]]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != rows:
        raise ModelContractError(f"{label} must have shape ({rows}, {columns}).")
    result = []
    for row in value:
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)) or len(row) != columns:
            raise ModelContractError(f"{label} must have shape ({rows}, {columns}).")
        converted = []
        for item in row:
            if isinstance(item, bool) or not isinstance(item, Real):
                raise ModelContractError(f"{label} must contain only real numbers.")
            number = float(item)
            if not math.isfinite(number):
                raise ModelContractError(f"{label} must contain only finite numbers.")
            converted.append(number)
        result.append(converted)
    return result
