from typing import Protocol


class ObservationPublisher(Protocol):
    """Publie une observation validée (payload ``observation.validated``,
    voir ``docs/events.md``)."""

    def publish(self, payload: dict) -> None: ...
