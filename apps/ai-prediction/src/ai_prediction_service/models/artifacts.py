import hashlib
import json
import re
from collections.abc import Callable, Set
from dataclasses import dataclass
from pathlib import Path

from .contract import INPUT_FEATURES, OUTPUT_FEATURES, validate_model_and_scalers
from .zones import ZONE_MODEL_MAPPING

ZONE_NUMBERS = frozenset(ZONE_MODEL_MAPPING)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ArtifactError(ValueError):
    """Artifact metadata or content is invalid."""


class ArtifactManifestError(ArtifactError):
    pass


class ArtifactNotFoundError(FileNotFoundError):
    pass


class ArtifactIntegrityError(ArtifactError):
    pass


class ArtifactTrustError(ArtifactError):
    pass


class UnknownZoneArtifactsError(KeyError):
    pass


APPROVAL_SEPARATORS = re.compile(r"[\s,;]+")


def parse_approved_scaler_digests(raw: str | None) -> frozenset[str]:
    """Parse AI_APPROVED_SCALER_SHA256 into normalized SHA-256 digests.

    Accepts commas, semicolons, spaces or newlines as separators, optional
    quotes, and uppercase hex (PowerShell ``Get-FileHash`` prints uppercase).
    Any entry that is not a SHA-256 digest is rejected instead of being
    silently ignored, so a malformed approval list is visible at startup.
    """
    digests = set()
    invalid = []
    for token in APPROVAL_SEPARATORS.split(raw or ""):
        token = token.strip().strip("'\"").lower()
        if not token:
            continue
        if SHA256_PATTERN.fullmatch(token):
            digests.add(token)
        else:
            invalid.append(token[:16] + ("…" if len(token) > 16 else ""))
    if invalid:
        raise ArtifactTrustError(
            "AI_APPROVED_SCALER_SHA256 contains values that are not SHA-256 digests: "
            + ", ".join(invalid)
        )
    return frozenset(digests)


@dataclass(frozen=True)
class ArtifactFile:
    path: Path
    sha256: str
    source_path: str
    git_blob: str


@dataclass(frozen=True)
class ZoneArtifactSpec:
    zone_number: int
    zone_code: str
    model: ArtifactFile
    scaler_x: ArtifactFile
    scaler_y: ArtifactFile


@dataclass(frozen=True)
class LoadedModelBundle:
    spec: ZoneArtifactSpec
    model: object
    scaler_x: object
    scaler_y: object


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


class ArtifactLoader:
    """Loads artifacts through injected functions after explicit trust checks.

    This class does not import TensorFlow or joblib. The scaler loader is only
    called when both scaler hashes have been approved and isolation has been
    explicitly confirmed by the caller.
    """

    def __init__(
        self,
        *,
        model_loader: Callable[[Path], object],
        scaler_loader: Callable[[Path], object],
    ):
        self._model_loader = model_loader
        self._scaler_loader = scaler_loader

    def load(
        self,
        spec: ZoneArtifactSpec,
        *,
        approved_scaler_sha256: Set[str] = frozenset(),
        isolated_environment: bool = False,
    ) -> LoadedModelBundle:
        if not isolated_environment:
            raise ArtifactTrustError("Artifact loading requires an isolated environment.")
        missing = [
            f"{label}={artifact.sha256}"
            for label, artifact in (("scaler_x", spec.scaler_x), ("scaler_y", spec.scaler_y))
            if artifact.sha256 not in approved_scaler_sha256
        ]
        if missing:
            raise ArtifactTrustError(
                "Both scaler SHA-256 values require explicit provenance approval. "
                f"Not approved for zone {spec.zone_code}: {', '.join(missing)} "
                f"({len(approved_scaler_sha256)} approved digest(s) configured)."
            )

        for artifact in (spec.model, spec.scaler_x, spec.scaler_y):
            _verify_artifact(artifact)

        model = self._model_loader(spec.model.path)
        scaler_x = self._scaler_loader(spec.scaler_x.path)
        scaler_y = self._scaler_loader(spec.scaler_y.path)
        validate_model_and_scalers(model, scaler_x, scaler_y)
        return LoadedModelBundle(spec, model, scaler_x, scaler_y)


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


def _verify_artifact(artifact: ArtifactFile) -> None:
    if not artifact.path.is_file():
        raise ArtifactNotFoundError(f"Artifact file is missing: {artifact.path}.")
    digest = hashlib.sha256()
    with artifact.path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != artifact.sha256:
        raise ArtifactIntegrityError(f"Artifact SHA-256 mismatch: {artifact.path}.")
