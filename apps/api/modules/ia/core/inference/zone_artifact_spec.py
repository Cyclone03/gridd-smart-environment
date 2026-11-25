from dataclasses import dataclass

from .artifact_file import ArtifactFile


@dataclass(frozen=True)
class ZoneArtifactSpec:
    zone_number: int
    zone_code: str
    model: ArtifactFile
    scaler_x: ArtifactFile
    scaler_y: ArtifactFile
