from dataclasses import dataclass

from .zone_artifact_spec import ZoneArtifactSpec


@dataclass(frozen=True)
class LoadedModelBundle:
    spec: ZoneArtifactSpec
    model: object
    scaler_x: object
    scaler_y: object
