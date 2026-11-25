from typing import Protocol

from modules.ia.core.domain.climate_prediction_event import ClimatePredictionEvent
from modules.ia.core.domain.publication_receipt import PublicationReceipt
from modules.ia.core.domain.weather_snapshot_event import WeatherSnapshotEvent


class PredictionPublisher(Protocol):
    """Publication confirmée des événements du module IA.

    Ne rend la main qu'après l'accusé de réception ; lève
    ``PredictionPublicationError`` sinon (la prédiction sera rejouée avec le
    même ``event_id`` au cycle suivant).
    """

    def publish_prediction(self, event: ClimatePredictionEvent) -> PublicationReceipt: ...

    def publish_weather_snapshot(self, event: WeatherSnapshotEvent) -> PublicationReceipt: ...
