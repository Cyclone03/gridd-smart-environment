from modules.realtime.services.realtime_groups import RealtimeGroups

from .broadcast_websocket import BroadcastWebSocket


class DashboardWebSocket(BroadcastWebSocket):
    """``/ws/dashboard/`` : toutes les mesures et les changements d'alertes."""

    group_name = RealtimeGroups.DASHBOARD
