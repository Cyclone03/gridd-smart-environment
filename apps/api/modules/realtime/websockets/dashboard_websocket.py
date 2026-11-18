import asyncio
import logging

from channels.db import database_sync_to_async

from modules.realtime.services.dashboard_snapshot_service import DashboardSnapshotService
from modules.realtime.services.realtime_groups import RealtimeGroups

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
    snapshot_service_class = DashboardSnapshotService

    SNAPSHOT_TIMEOUT_SECONDS = 15.0

    async def connect(self):
        await super().connect()
        if self.joined:
            await self.send_snapshot()

    async def receive_json(self, content, **kwargs):
        action = content.get("action") if isinstance(content, dict) else None
        if action == "snapshot":
            await self.send_snapshot()
        else:
            await super().receive_json(content, **kwargs)

    async def send_snapshot(self):
        try:
            snapshot = await asyncio.wait_for(
                database_sync_to_async(self.snapshot_service_class().snapshot)(), self.SNAPSHOT_TIMEOUT_SECONDS
            )
        except Exception:
            logger.exception("Impossible de construire l'instantané du tableau de bord.")
            await self.send_json(
                {"event": "dashboard.error", "detail": "Le serveur GRIDD ne peut pas lire les données pour le moment."}
            )
            return
        await self.send_json({"event": "dashboard.snapshot", "data": snapshot})
