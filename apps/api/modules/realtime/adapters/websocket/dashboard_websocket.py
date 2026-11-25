import logging

from channels.db import database_sync_to_async

from modules.realtime.core.domain.realtime_groups import RealtimeGroups

from .broadcast_websocket import BroadcastWebSocket

logger = logging.getLogger(__name__)


class DashboardWebSocket(BroadcastWebSocket):
    """``/ws/dashboard/`` : source unique des données du tableau de bord.

    À l'ouverture (et à chaque reconnexion), le serveur envoie un instantané
    complet ``dashboard.snapshot`` (zones, dernières mesures, alertes), puis
    les changements au fil de l'eau. Le client peut redemander l'instantané
    avec ``{"action": "snapshot"}`` (bouton « Rafraîchir ») et vérifier la
    connexion avec ``{"action": "ping"}`` (réponse ``{"event": "pong"}``).
    """

    group_name = RealtimeGroups.DASHBOARD

    async def connect(self):
        await super().connect()
        await self.send_snapshot()

    async def receive_json(self, content, **kwargs):
        action = content.get("action") if isinstance(content, dict) else None
        if action == "snapshot":
            await self.send_snapshot()
        else:
            await super().receive_json(content, **kwargs)

    @staticmethod
    def build_snapshot():
        # Import tardif : la composition charge les adaptateurs Django (ORM).
        from modules.realtime.composition import dashboard_snapshot_service

        return dashboard_snapshot_service().snapshot()

    async def send_snapshot(self):
        try:
            snapshot = await database_sync_to_async(self.build_snapshot)()
        except Exception:
            logger.exception("Impossible de construire l'instantané du tableau de bord.")
            await self.send_json(
                {"event": "dashboard.error", "detail": "Le serveur GRIDD ne peut pas lire les données pour le moment."}
            )
            return
        await self.send_json({"event": "dashboard.snapshot", "data": snapshot})
