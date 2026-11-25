from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArtifactFile:
    path: Path
    sha256: str
    source_path: str
    git_blob: str
