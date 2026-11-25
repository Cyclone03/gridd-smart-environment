from channels.generic.websocket import AsyncJsonWebsocketConsumer


class BroadcastWebSocket(AsyncJsonWebsocketConsumer):
    """Connexion WebSocket abonnée à un groupe de diffusion.

    Messages envoyés au client :
    - ``{"event": "realtime.connected"}`` à l'ouverture ;
    - ``{"event": "observation.created", "data": {...}}`` pour une mesure, ou
      ``{"event": "observations.created", "data": [...]}`` pour un lot ;
    - ``{"event": "climate_prediction.created", "data": {...}}`` pour une prédiction ;
    - ``{"event": "alerts.changed", "data": {"active": [...], "history": [...]}}``
      lorsqu'une alerte est créée, résolue ou modifiée ;
    - ``{"event": "zones.changed", "data": [...]}`` lorsque la liste des zones change.
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

    async def observations_created(self, event):
        await self.send_json({"event": "observations.created", "data": event["payload"]})

    async def climate_prediction_created(self, event):
        await self.send_json({"event": "climate_prediction.created", "data": event["payload"]})

    async def weather_snapshot_created(self, event):
        await self.send_json({"event": "weather_snapshot.created", "data": event["payload"]})

    async def receive_json(self, content, **kwargs):
        if isinstance(content, dict) and content.get("action") == "ping":
            await self.refresh_membership()
            await self.send_json({"event": "pong"})

    async def refresh_membership(self):
        """Renouvelle l'inscription au groupe.

        Les inscriptions expirent (``group_expiry``, quelques minutes) : une
        connexion coupée sans ``disconnect`` (redémarrage de l'API) sort donc
        d'elle-même du groupe au lieu d'y accumuler des messages pendant 24 h.
        Le navigateur envoie un ``ping`` toutes les 25 s, ce qui garde les
        connexions vivantes inscrites.
        """
        await self.channel_layer.group_add(self.group_name, self.channel_name)

    async def alerts_changed(self, event):
        await self.send_json({"event": "alerts.changed", "data": event.get("payload")})

    async def zones_changed(self, event):
        await self.send_json({"event": "zones.changed", "data": event.get("payload")})
