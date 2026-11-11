from modules.realtime.services.realtime_broadcaster import RealtimeBroadcaster
from shared.contracts.event_types import EventTypes
from shared.messaging import EventHandler


class RealtimeConsumer(EventHandler):
    """Relaie aux navigateurs les faits persistés par le module Database :
    les tableaux de bord ne reçoivent que des données réellement enregistrées."""

    def __init__(self, broadcaster):
        self._broadcaster = broadcaster

    @classmethod
    def build(cls):
        return cls(RealtimeBroadcaster())

    def routes(self):
        return {
            EventTypes.OBSERVATION_PERSISTED: lambda event: self._broadcaster.observation_created(event.payload),
            EventTypes.ALERTS_CHANGED: lambda event: self._broadcaster.alerts_changed(),
        }
