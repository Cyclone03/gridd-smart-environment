import json
from pathlib import Path

from modules.ia.core.domain.zones import ZONE_MODEL_MAPPING
from modules.ia.core.errors import ArtifactManifestError, UnknownZoneArtifactsError

from .artifact_file import ArtifactFile
from .contract import INPUT_FEATURES, OUTPUT_FEATURES
from .scaler_approval import SHA256_PATTERN
from .zone_artifact_spec import ZoneArtifactSpec

ZONE_NUMBERS = frozenset(ZONE_MODEL_MAPPING)


class ArtifactRegistry:
    """Binds numbered artifact bundles to explicit Django zone codes."""

    def __init__(self, manifest_path: Path):
        manifest_path = Path(manifest_path)
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactManifestError(f"Cannot read artifact manifest: {manifest_path}.") from exc
        if not isinstance(manifest, dict) or not isinstance(manifest.get("zones"), dict):
            raise ArtifactManifestError("Artifact manifest must contain a zones object.")

        _validate_confirmed_contract(manifest.get("contract"))
        zones = manifest["zones"]
        if set(zones) != {str(number) for number in ZONE_NUMBERS}:
            raise ArtifactManifestError("Manifest must describe exactly model zones 1 through 6.")

        root = manifest_path.parent.resolve()
        specs = {}
        for number in sorted(ZONE_NUMBERS):
            record = zones[str(number)]
            if not isinstance(record, dict):
                raise ArtifactManifestError(f"Manifest entry for model zone {number} is invalid.")
            files = record.get("files")
            if not isinstance(files, dict):
                raise ArtifactManifestError(f"Manifest entry for model zone {number} has no files.")
            zone_code = ZONE_MODEL_MAPPING[number]
            if record.get("zone_code") != zone_code:
                raise ArtifactManifestError(
                    f"Manifest mapping for model zone {number} must be {zone_code!r}."
                )
            if record.get("zone_code_mapping_status") != "confirmed_by_Karina":
                raise ArtifactManifestError(
                    f"Manifest mapping for model zone {number} is not confirmed by Karina."
                )
            spec = ZoneArtifactSpec(
                zone_number=number,
                zone_code=zone_code,
                model=_artifact_file(root, files.get("model"), f"zone {number} model"),
                scaler_x=_artifact_file(root, files.get("scaler_x"), f"zone {number} scaler X"),
                scaler_y=_artifact_file(root, files.get("scaler_y"), f"zone {number} scaler Y"),
            )
            specs[spec.zone_code] = spec
        self._specs = specs

    def for_zone(self, zone_code: str) -> ZoneArtifactSpec:
        try:
            return self._specs[zone_code]
        except KeyError as exc:
            raise UnknownZoneArtifactsError(f"No model bundle is registered for zone {zone_code!r}.") from exc

    def zone_codes(self) -> tuple[str, ...]:
        return tuple(self._specs)


def _validate_confirmed_contract(contract: object) -> None:
    if not isinstance(contract, dict):
        raise ArtifactManifestError("Artifact manifest must contain a confirmed contract.")
    if contract.get("input_features") != list(INPUT_FEATURES):
        raise ArtifactManifestError("Manifest input feature order does not match the confirmed contract.")
    if contract.get("output_features") != list(OUTPUT_FEATURES):
        raise ArtifactManifestError("Manifest output feature order does not match the confirmed contract.")
    for status_field in ("input_order_status", "output_order_status", "zone_mapping_status"):
        if contract.get(status_field) != "confirmed_by_Karina":
            raise ArtifactManifestError(f"Manifest field {status_field!r} is not confirmed by Karina.")
    expected_mapping = {str(number): code for number, code in ZONE_MODEL_MAPPING.items()}
    if contract.get("zone_model_mapping") != expected_mapping:
        raise ArtifactManifestError("Manifest zone mapping does not match the confirmed mapping.")


def _artifact_file(root: Path, value: object, label: str) -> ArtifactFile:
    if not isinstance(value, dict):
        raise ArtifactManifestError(f"Missing file record for {label}.")
    relative_path = value.get("path")
    sha256 = value.get("sha256")
    source_path = value.get("source_path")
    git_blob = value.get("git_blob")
    if not isinstance(relative_path, str) or not relative_path:
        raise ArtifactManifestError(f"Missing artifact path for {label}.")
    if not isinstance(sha256, str) or not SHA256_PATTERN.fullmatch(sha256):
        raise ArtifactManifestError(f"Invalid SHA-256 for {label}.")
    if not isinstance(source_path, str) or not source_path:
        raise ArtifactManifestError(f"Missing source path for {label}.")
    if not isinstance(git_blob, str) or not git_blob:
        raise ArtifactManifestError(f"Missing Git blob id for {label}.")
    path = (root / relative_path).resolve()
    if path != root and root not in path.parents:
        raise ArtifactManifestError(f"Artifact path escapes its manifest directory: {relative_path}.")
    return ArtifactFile(path, sha256, source_path, git_blob)
