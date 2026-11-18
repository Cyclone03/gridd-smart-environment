import asyncio
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class BroadcastWebSocket(AsyncJsonWebsocketConsumer):
    """Connexion WebSocket abonnée à un groupe de diffusion.

    Messages envoyés au client :
    - ``{"event": "realtime.connected"}`` à l'ouverture ;
    - ``{"event": "observation.created", "data": {...}}`` pour une mesure, ou
      ``{"event": "observations.created", "data": [...]}`` pour un lot ;
    - ``{"event": "alerts.changed", "data": {"active": [...], "history": [...]}}``
      lorsqu'une alerte est créée, résolue ou modifiée ;
    - ``{"event": "zones.changed", "data": [...]}`` lorsque la liste des zones change.
    """

    group_name = None
    # Délai maximal d'un appel au channel layer (Redis).
    CHANNEL_TIMEOUT_SECONDS = 5.0
    # Code de fermeture « réessayer plus tard » : le navigateur se reconnecte.
    TRY_AGAIN_LATER = 1013

    joined = False

    async def connect(self):
        # Accepter d'abord : Daphne coupe une connexion non acceptée après 5 s,
        # et une tâche bloquée sur Redis ne pouvait plus être arrêtée
        # (« took too long to shut down and was killed »).
        await self.accept()
        self.joined = await self._channel_call(self.channel_layer.group_add, "inscription")
        if not self.joined:
            await self.send_json(
                {"event": "dashboard.error", "detail": "Temps réel momentanément indisponible. Nouvelle tentative…"}
            )
            await self.close(code=self.TRY_AGAIN_LATER)
            return
        await self.send_json(self.connected_message())

    def connected_message(self):
        return {"event": "realtime.connected"}

    async def disconnect(self, close_code):
        if self.joined:
            await self._channel_call(self.channel_layer.group_discard, "désinscription")

    async def _channel_call(self, operation, label) -> bool:
        """Appel au channel layer borné dans le temps ; ``False`` en cas d'échec."""
        try:
            await asyncio.wait_for(operation(self.group_name, self.channel_name), self.CHANNEL_TIMEOUT_SECONDS)
            return True
        except Exception as exc:
            logger.warning("WebSocket %s : %s impossible (%s).", self.group_name, label, exc.__class__.__name__ or exc)
            return False

    async def observation_created(self, event):
        await self.send_json({"event": "observation.created", "data": event["payload"]})

    async def observations_created(self, event):
        await self.send_json({"event": "observations.created", "data": event["payload"]})

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
        await self._channel_call(self.channel_layer.group_add, "renouvellement")

    async def alerts_changed(self, event):
        await self.send_json({"event": "alerts.changed", "data": event.get("payload")})

    async def zones_changed(self, event):
        await self.send_json({"event": "zones.changed", "data": event.get("payload")})
