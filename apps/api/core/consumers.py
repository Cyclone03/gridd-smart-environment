from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .realtime import DASHBOARD_GROUP, zone_group


class _BroadcastConsumer(AsyncJsonWebsocketConsumer):
    """Relaie aux navigateurs les événements publiés par ``core.realtime``.

    Messages envoyés au client :
    - ``{"event": "realtime.connected"}`` à l'ouverture ;
    - ``{"event": "observation.created", "data": {...}}`` pour chaque mesure ;
    - ``{"event": "alerts.changed"}`` lorsqu'une alerte est créée ou résolue
      (tableau de bord global uniquement).
    """

    group_name = None

    async def connect(self):
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json(self.connected_message())

    def connected_message(self):
        return {"event": "realtime.connected"}

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def observation_created(self, event):
        await self.send_json({"event": "observation.created", "data": event["payload"]})

    async def alerts_changed(self, event):
        await self.send_json({"event": "alerts.changed"})


class DashboardConsumer(_BroadcastConsumer):
    group_name = DASHBOARD_GROUP


class ZoneRealtimeConsumer(_BroadcastConsumer):
    async def connect(self):
        self.zone_code = self.scope["url_route"]["kwargs"]["zone_code"]
        self.group_name = zone_group(self.zone_code)
        await super().connect()

    def connected_message(self):
        return {"event": "realtime.connected", "zone": self.zone_code}
