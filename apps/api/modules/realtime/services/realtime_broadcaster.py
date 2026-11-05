import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .realtime_groups import RealtimeGroups

logger = logging.getLogger(__name__)


class RealtimeBroadcaster:
    """Diffusion vers les navigateurs connectés (Django Channels).

    Une panne du channel layer (Redis indisponible) est journalisée puis
    ignorée : la donnée est déjà enregistrée et un rejeu Kafka n'apporterait rien.
    """

    def observation_created(self, payload):
        self._send(
            [RealtimeGroups.DASHBOARD, RealtimeGroups.zone(payload["zone_code"])],
            {"type": "observation.created", "payload": payload},
        )

    def alerts_changed(self):
        self._send([RealtimeGroups.DASHBOARD], {"type": "alerts.changed"})

    def comfort_updated(self, payload):
        self._send(
            [RealtimeGroups.DASHBOARD, RealtimeGroups.zone(payload["zone_code"])],
            {"type": "comfort.updated", "payload": payload},
        )

    def energy_updated(self, payload):
        self._send([RealtimeGroups.DASHBOARD], {"type": "energy.updated", "payload": {"zone_code": payload["zone_code"]}})

    @staticmethod
    def _send(groups, event):
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning("Aucun channel layer configuré : événement %s non diffusé.", event["type"])
            return
        try:
            for group in groups:
                async_to_sync(channel_layer.group_send)(group, event)
        except Exception:
            logger.exception("Impossible de diffuser l'événement %s.", event["type"])
