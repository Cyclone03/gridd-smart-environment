import math
from collections.abc import Mapping
from numbers import Real

from modules.ia.core.errors import ModelContractError

MODEL_INPUT_SHAPE = (None, 4, 1)
MODEL_OUTPUT_SHAPE = (None, 2)

INPUT_FEATURES = (
    "indoor_temperature",
    "indoor_humidity",
    "outdoor_temperature",
    "outdoor_humidity",
)
INPUT_UNITS = ("°C", "%", "°C", "%")
OUTPUT_FEATURES = ("indoor_temperature", "indoor_humidity")
OUTPUT_UNITS = ("°C", "%")


def ordered_input_values(values: object) -> tuple[float, float, float, float]:
    if not isinstance(values, Mapping):
        raise ModelContractError("Input must map each confirmed feature name to a numeric value.")
    missing = [feature for feature in INPUT_FEATURES if feature not in values]
    unexpected = [feature for feature in values if feature not in INPUT_FEATURES]
    if missing or unexpected:
        raise ModelContractError(
            f"Input features must be exactly {INPUT_FEATURES}; "
            f"missing={missing}, unexpected={unexpected}."
        )

    parsed = []
    for index, feature in enumerate(INPUT_FEATURES):
        value = values[feature]
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ModelContractError(f"Input feature {feature!r} must be a real number.")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ModelContractError(f"Input feature {feature!r} must be finite.")
        parsed.append(numeric)
    return tuple(parsed)


def validate_model_and_scalers(model: object, scaler_x: object, scaler_y: object) -> None:
    input_shape = _single_shape(model, "input_shape")
    output_shape = _single_shape(model, "output_shape")
    if input_shape != MODEL_INPUT_SHAPE:
        raise ModelContractError(
            f"Model input shape must be {MODEL_INPUT_SHAPE}, received {input_shape}."
        )
    if output_shape != MODEL_OUTPUT_SHAPE:
        raise ModelContractError(
            f"Model output shape must be {MODEL_OUTPUT_SHAPE}, received {output_shape}."
        )
    _validate_scaler_features(scaler_x, 4, "X")
    _validate_scaler_features(scaler_y, 2, "Y")


def _single_shape(model: object, attribute: str) -> tuple[int | None, ...]:
    shape = getattr(model, attribute, None)
    if isinstance(shape, list) and len(shape) == 1 and isinstance(shape[0], (list, tuple)):
        shape = shape[0]
    elif isinstance(shape, list) and shape and isinstance(shape[0], (list, tuple)):
        raise ModelContractError(f"Multiple model {attribute.removesuffix('_shape')}s are unsupported.")
    if shape is None:
        raise ModelContractError(f"Model does not expose {attribute}.")
    try:
        return tuple(_dimension_value(dimension) for dimension in shape)
    except (TypeError, ValueError) as exc:
        raise ModelContractError(f"Model exposes an invalid {attribute}.") from exc


def _dimension_value(value: object) -> int | None:
    value = getattr(value, "value", value)
    return None if value is None else int(value)


def _validate_scaler_features(scaler: object, expected: int, label: str) -> None:
    actual = getattr(scaler, "n_features_in_", None)
    if isinstance(actual, bool) or actual != expected:
        raise ModelContractError(
            f"Scaler {label} must expose n_features_in_={expected}, received {actual!r}."
        )
