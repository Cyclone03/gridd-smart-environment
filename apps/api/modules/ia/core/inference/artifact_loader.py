import hashlib
from collections.abc import Callable, Set
from pathlib import Path

from modules.ia.core.errors import ArtifactIntegrityError, ArtifactNotFoundError, ArtifactTrustError

from .artifact_file import ArtifactFile
from .contract import validate_model_and_scalers
from .loaded_model_bundle import LoadedModelBundle
from .zone_artifact_spec import ZoneArtifactSpec


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


def _verify_artifact(artifact: ArtifactFile) -> None:
    if not artifact.path.is_file():
        raise ArtifactNotFoundError(f"Artifact file is missing: {artifact.path}.")
    digest = hashlib.sha256()
    with artifact.path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != artifact.sha256:
        raise ArtifactIntegrityError(f"Artifact SHA-256 mismatch: {artifact.path}.")
