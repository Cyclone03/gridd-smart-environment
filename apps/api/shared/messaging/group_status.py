from dataclasses import dataclass, field

from .partition_status import PartitionStatus


@dataclass(frozen=True)
class GroupStatus:
    """État d'un consumer group : membres (avec leurs partitions) et partitions."""

    group: str
    state: str
    members: list[tuple[str, list[tuple[str, int]]]] = field(default_factory=list)
    partitions: list[PartitionStatus] = field(default_factory=list)
