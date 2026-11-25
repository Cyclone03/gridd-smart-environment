from typing import Protocol


class ReadingPublisher(Protocol):
    """Publie une mesure au format capteur GRIDD."""

    def supports(self, metric) -> bool:
        """Vrai si un canal de publication existe pour ce type de mesure."""

    def publish(self, metric, node_id, message: dict) -> None: ...
