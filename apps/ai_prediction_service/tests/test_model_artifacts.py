import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from ai_prediction_service.models.artifacts import (
    ArtifactIntegrityError,
    ArtifactLoader,
    ArtifactManifestError,
    ArtifactNotFoundError,
    ArtifactRegistry,
    ArtifactTrustError,
)
from ai_prediction_service.models.contract import INPUT_FEATURES, OUTPUT_FEATURES
from ai_prediction_service.models.zones import ZONE_MODEL_MAPPING


class FakeModel:
    input_shape = (None, 4, 1)
    output_shape = (None, 2)


class FakeScalerX:
    n_features_in_ = 4


class FakeScalerY:
    n_features_in_ = 2


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        zones = {}
        for number in range(1, 7):
            zone_dir = self.root / f"zone{number}"
            zone_dir.mkdir()
            files = {}
            for kind, filename in (
                ("model", f"modelZone{number}.h5"),
                ("scaler_x", f"scalerX_zone{number}.joblib"),
                ("scaler_y", f"scalerY_zone{number}.joblib"),
            ):
                content = f"test-only-{kind}-{number}".encode()
                path = zone_dir / filename
                path.write_bytes(content)
                files[kind] = {
                    "path": f"zone{number}/{filename}",
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "source_path": f"apps/api/{filename}",
                    "git_blob": f"blob-{kind}-{number}",
                }
            zones[str(number)] = {
                "files": files,
                "zone_code": ZONE_MODEL_MAPPING[number],
                "zone_code_mapping_status": "confirmed_by_Karina",
            }
        self.manifest_path = self.root / "manifest.json"
        manifest = {
            "schema_version": 2,
            "contract": {
                "input_features": list(INPUT_FEATURES),
                "input_order_status": "confirmed_by_Karina",
                "output_features": list(OUTPUT_FEATURES),
                "output_order_status": "confirmed_by_Karina",
                "zone_mapping_status": "confirmed_by_Karina",
                "zone_model_mapping": {str(number): code for number, code in ZONE_MODEL_MAPPING.items()},
            },
            "zones": zones,
        }
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_centralized_zone_mapping_resolves_each_bundle(self):
        registry = ArtifactRegistry(self.manifest_path)

        for number, zone_code in ZONE_MODEL_MAPPING.items():
            with self.subTest(number=number):
                spec = registry.for_zone(zone_code)
                self.assertEqual(spec.zone_number, number)
                self.assertEqual(
                    spec.model.path,
                    self.root / f"zone{number}" / f"modelZone{number}.h5",
                )
                self.assertEqual(
                    spec.scaler_x.path,
                    self.root / f"zone{number}" / f"scalerX_zone{number}.joblib",
                )
                self.assertEqual(
                    spec.scaler_y.path,
                    self.root / f"zone{number}" / f"scalerY_zone{number}.joblib",
                )
        self.assertEqual(len(registry.zone_codes()), 6)

    def test_manifest_mapping_must_match_centralized_mapping(self):
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["zones"]["1"]["zone_code"] = "meeting-room"
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        with self.assertRaisesRegex(ArtifactManifestError, "must be 'open-workspace'"):
            ArtifactRegistry(self.manifest_path)

    def test_unknown_zone_is_rejected(self):
        registry = ArtifactRegistry(self.manifest_path)

        with self.assertRaises(KeyError):
            registry.for_zone("unmapped")

    def test_artifact_presence_is_checked(self):
        registry = ArtifactRegistry(self.manifest_path)
        spec = registry.for_zone(ZONE_MODEL_MAPPING[1])
        spec.scaler_y.path.unlink()
        loader = ArtifactLoader(model_loader=Mock(), scaler_loader=Mock())
        approvals = {spec.scaler_x.sha256, spec.scaler_y.sha256}

        with self.assertRaises(ArtifactNotFoundError):
            loader.load(spec, approved_scaler_sha256=approvals, isolated_environment=True)

    def test_scaler_loading_requires_isolation_and_hash_approval(self):
        registry = ArtifactRegistry(self.manifest_path)
        spec = registry.for_zone(ZONE_MODEL_MAPPING[1])
        model_loader = Mock(return_value=FakeModel())
        scaler_loader = Mock(side_effect=[FakeScalerX(), FakeScalerY()])
        loader = ArtifactLoader(model_loader=model_loader, scaler_loader=scaler_loader)

        with self.assertRaises(ArtifactTrustError):
            loader.load(spec)
        self.assertFalse(model_loader.called)
        self.assertFalse(scaler_loader.called)

        with self.assertRaises(ArtifactTrustError):
            loader.load(spec, isolated_environment=True)
        self.assertFalse(model_loader.called)
        self.assertFalse(scaler_loader.called)

    def test_approved_artifacts_load_with_injected_test_doubles(self):
        registry = ArtifactRegistry(self.manifest_path)
        spec = registry.for_zone(ZONE_MODEL_MAPPING[2])
        loader = ArtifactLoader(
            model_loader=Mock(return_value=FakeModel()),
            scaler_loader=Mock(side_effect=[FakeScalerX(), FakeScalerY()]),
        )

        bundle = loader.load(
            spec,
            approved_scaler_sha256={spec.scaler_x.sha256, spec.scaler_y.sha256},
            isolated_environment=True,
        )

        self.assertEqual(bundle.spec.zone_code, ZONE_MODEL_MAPPING[2])

    def test_tampered_file_fails_hash_check_before_deserialization(self):
        registry = ArtifactRegistry(self.manifest_path)
        spec = registry.for_zone(ZONE_MODEL_MAPPING[1])
        spec.scaler_x.path.write_bytes(b"tampered test data")
        model_loader = Mock()
        scaler_loader = Mock()
        loader = ArtifactLoader(model_loader=model_loader, scaler_loader=scaler_loader)

        with self.assertRaises(ArtifactIntegrityError):
            loader.load(
                spec,
                approved_scaler_sha256={spec.scaler_x.sha256, spec.scaler_y.sha256},
                isolated_environment=True,
            )
        self.assertFalse(model_loader.called)
        self.assertFalse(scaler_loader.called)


if __name__ == "__main__":
    unittest.main()
