from modules.realtime.services.realtime_groups import RealtimeGroups

from .broadcast_websocket import BroadcastWebSocket


class ZoneWebSocket(BroadcastWebSocket):
    """``/ws/zones/<code>/`` : mesures d'une zone."""

    async def connect(self):
        self.zone_code = self.scope["url_route"]["kwargs"]["zone_code"]
        self.group_name = RealtimeGroups.zone(self.zone_code)
        await super().connect()

    def connected_message(self):
        return {"event": "realtime.connected", "zone": self.zone_code}
