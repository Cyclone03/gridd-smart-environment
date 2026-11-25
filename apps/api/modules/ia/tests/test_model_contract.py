import unittest

from modules.ia.core.errors import ModelContractError
from modules.ia.core.inference.contract import (
    INPUT_FEATURES,
    OUTPUT_FEATURES,
    ordered_input_values,
    validate_model_and_scalers,
)


class FakeModel:
    input_shape = (None, 4, 1)
    output_shape = (None, 2)


class FakeScalerX:
    n_features_in_ = 4


class FakeScalerY:
    n_features_in_ = 2


class ModelContractTests(unittest.TestCase):
    def test_confirmed_input_and_output_feature_order(self):
        self.assertEqual(
            INPUT_FEATURES,
            ("indoor_temperature", "indoor_humidity", "outdoor_temperature", "outdoor_humidity"),
        )
        self.assertEqual(OUTPUT_FEATURES, ("indoor_temperature", "indoor_humidity"))

    def test_orders_named_features_independently_of_mapping_insertion_order(self):
        features = {
            "outdoor_humidity": 60,
            "outdoor_temperature": 12,
            "indoor_humidity": 45,
            "indoor_temperature": 20,
        }

        self.assertEqual(ordered_input_values(features), (20.0, 45.0, 12.0, 60.0))

    def test_rejects_missing_or_unexpected_feature_names(self):
        with self.assertRaisesRegex(ModelContractError, "missing"):
            ordered_input_values({"indoor_temperature": 20})
        with self.assertRaisesRegex(ModelContractError, "unexpected"):
            ordered_input_values(
                {
                    "indoor_temperature": 20,
                    "indoor_humidity": 45,
                    "outdoor_temperature": 12,
                    "outdoor_humidity": 60,
                    "wind_speed": 5,
                }
            )

    def test_rejects_boolean_and_non_finite_features(self):
        features = {
            "indoor_temperature": 20,
            "indoor_humidity": 45,
            "outdoor_temperature": 12,
            "outdoor_humidity": 60,
        }
        for feature, value in (("indoor_humidity", True), ("outdoor_temperature", float("nan"))):
            invalid = {**features, feature: value}
            with self.subTest(features=invalid), self.assertRaises(ModelContractError):
                ordered_input_values(invalid)

    def test_validates_model_and_scaler_shapes(self):
        validate_model_and_scalers(FakeModel(), FakeScalerX(), FakeScalerY())

    def test_rejects_incompatible_model_or_scaler_shapes(self):
        class BadModel(FakeModel):
            input_shape = (None, 4)

        with self.assertRaisesRegex(ModelContractError, "input shape"):
            validate_model_and_scalers(BadModel(), FakeScalerX(), FakeScalerY())

        class BadScaler:
            n_features_in_ = 5

        with self.assertRaisesRegex(ModelContractError, "n_features_in_"):
            validate_model_and_scalers(FakeModel(), BadScaler(), FakeScalerY())
