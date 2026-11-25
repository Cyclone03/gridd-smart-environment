from modules.realtime.core.services.realtime_relay_service import RealtimeRelayService
from shared.kernel.events import EventTypes
from shared.messaging import EventHandler


class RealtimeConsumer(EventHandler):
    """Abonnement Kafka (``database.events``) du module Realtime : traduit
    chaque fait persisté en appel du ``RealtimeRelayService``."""

    def __init__(self, broadcaster, snapshots):
        self._relay = RealtimeRelayService(broadcaster, snapshots)

    def routes(self):
        return {
            EventTypes.OBSERVATION_PERSISTED: lambda event: self._relay.observation_persisted(event.payload),
            EventTypes.CLIMATE_PREDICTION_PERSISTED: self._relay.climate_prediction_persisted,
            EventTypes.WEATHER_SNAPSHOT_PERSISTED: self._relay.weather_snapshot_persisted,
            EventTypes.ALERTS_CHANGED: lambda event: self._relay.alerts_changed(),
            EventTypes.ZONES_CHANGED: lambda event: self._relay.zones_changed(),
        }

    def begin_batch(self):
        self._relay.begin_batch()

    def end_batch(self):
        self._relay.end_batch()
