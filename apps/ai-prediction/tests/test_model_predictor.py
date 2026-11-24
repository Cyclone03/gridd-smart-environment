import unittest
from dataclasses import dataclass

import numpy as np

from ai_prediction_service.models.artifacts import LoadedModelBundle, ZoneArtifactSpec
from ai_prediction_service.models.contract import ModelContractError
from ai_prediction_service.models.predictor import ModelPredictor


@dataclass(frozen=True)
class DummyArtifact:
    path: str = "test-only"
    sha256: str = "0" * 64
    source_path: str = "test-only"
    git_blob: str = "test-only"


class FakeModel:
    input_shape = (None, 4, 1)
    output_shape = (None, 2)

    def __init__(self):
        self.received = None
        self.output = [[0.25, 0.75]]

    def predict(self, values, *, verbose=0):
        self.received = values
        return self.output


class FakeScalerX:
    n_features_in_ = 4

    def __init__(self):
        self.received = None

    def transform(self, rows):
        self.received = rows
        return [[value / 100 for value in rows[0]]]


class FakeScalerY:
    n_features_in_ = 2

    def inverse_transform(self, rows):
        return [[rows[0][0] * 40, rows[0][1] * 100]]


class ModelPredictorTests(unittest.TestCase):
    def setUp(self):
        self.model = FakeModel()
        self.scaler_x = FakeScalerX()
        self.bundle = LoadedModelBundle(
            spec=ZoneArtifactSpec(
                zone_number=1,
                zone_code="open-workspace",
                model=DummyArtifact(),
                scaler_x=DummyArtifact(),
                scaler_y=DummyArtifact(),
            ),
            model=self.model,
            scaler_x=self.scaler_x,
            scaler_y=FakeScalerY(),
        )

    def test_prediction_path_reshapes_scaled_values_and_inverse_transforms(self):
        predictor = ModelPredictor({"open-workspace": self.bundle})

        result = predictor.predict_one(
            "open-workspace",
            {
                "outdoor_humidity": 60,
                "outdoor_temperature": 12,
                "indoor_humidity": 45,
                "indoor_temperature": 20,
            },
        )

        self.assertEqual(self.scaler_x.received, [[20.0, 45.0, 12.0, 60.0]])
        self.assertIsInstance(self.model.received, np.ndarray)
        self.assertEqual(self.model.received.dtype, np.dtype(np.float32))
        self.assertEqual(self.model.received.shape, (1, 4, 1))
        np.testing.assert_array_equal(
            self.model.received[0, :, 0],
            np.asarray([0.2, 0.45, 0.12, 0.6], dtype=np.float32),
        )
        self.assertEqual(result, (10.0, 75.0))

    def test_non_numeric_and_non_finite_features_are_rejected(self):
        predictor = ModelPredictor({"open-workspace": self.bundle})
        features = {
            "indoor_temperature": 20,
            "indoor_humidity": 45,
            "outdoor_temperature": 12,
            "outdoor_humidity": 60,
        }

        for feature, value in (
            ("indoor_temperature", "20"),
            ("outdoor_temperature", float("nan")),
            ("outdoor_humidity", float("inf")),
        ):
            with self.subTest(feature=feature, value=value):
                invalid_features = {**features, feature: value}
                with self.assertRaises(ModelContractError):
                    predictor.predict_one("open-workspace", invalid_features)

    def test_model_output_must_have_two_values(self):
        predictor = ModelPredictor({"open-workspace": self.bundle})
        self.model.output = [[0.25]]

        with self.assertRaisesRegex(ModelContractError, "model output must have shape"):
            predictor.predict_one(
                "open-workspace",
                {
                    "indoor_temperature": 20,
                    "indoor_humidity": 45,
                    "outdoor_temperature": 12,
                    "outdoor_humidity": 60,
                },
            )

    def test_bundle_must_match_centralized_zone_mapping(self):
        with self.assertRaisesRegex(ModelContractError, "must map to 'open-workspace'"):
            ModelPredictor({"meeting-room": self.bundle})

    def test_unknown_zone_is_rejected(self):
        predictor = ModelPredictor({"open-workspace": self.bundle})

        with self.assertRaises(KeyError):
            predictor.predict_one("unknown-zone", {})


if __name__ == "__main__":
    unittest.main()
