from typing import Protocol


class ObservationPresenter(Protocol):
    """Payload ``observation.persisted`` d'une observation enregistrée."""

    def to_payload(self, observation) -> dict: ...
