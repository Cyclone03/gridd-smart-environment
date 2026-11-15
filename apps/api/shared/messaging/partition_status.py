from dataclasses import dataclass


@dataclass(frozen=True)
class PartitionStatus:
    """Une partition d'un consumer group : membre qui la lit, position validée, fin."""

    topic: str
    partition: int
    owner: str | None
    committed: int | None
    end: int | None

    @property
    def lag(self) -> int | None:
        if self.end is None:
            return None
        return self.end - (self.committed if self.committed is not None else 0)
