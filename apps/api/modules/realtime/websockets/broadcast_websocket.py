from channels.generic.websocket import AsyncJsonWebsocketConsumer


class BroadcastWebSocket(AsyncJsonWebsocketConsumer):
    """Connexion WebSocket abonnée à un groupe de diffusion.

    Messages envoyés au client :
    - ``{"event": "realtime.connected"}`` à l'ouverture ;
    - ``{"event": "observation.created", "data": {...}}`` pour chaque mesure ;
    - ``{"event": "alerts.changed"}`` lorsqu'une alerte est créée ou résolue ;
    - ``{"event": "comfort.updated", "data": {...}}`` pour chaque évaluation de confort ;
    - ``{"event": "energy.updated", "data": {"zone_code": ...}}`` après une estimation d'énergie.
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

    async def comfort_updated(self, event):
        await self.send_json({"event": "comfort.updated", "data": event["payload"]})

    async def energy_updated(self, event):
        await self.send_json({"event": "energy.updated", "data": event["payload"]})
