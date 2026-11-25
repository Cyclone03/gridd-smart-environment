"""Racine de composition du module Realtime."""

from django.conf import settings

from modules.realtime.adapters.messaging.realtime_consumer import RealtimeConsumer
from modules.realtime.adapters.persistence.dashboard_payload_mapper import DashboardPayloadMapper
from modules.realtime.adapters.persistence.dashboard_repository import DashboardRepository
from modules.realtime.adapters.websocket.realtime_broadcaster import RealtimeBroadcaster
from modules.realtime.core.services.dashboard_snapshot_service import DashboardSnapshotService


def dashboard_snapshot_service() -> DashboardSnapshotService:
    return DashboardSnapshotService(
        repository=DashboardRepository(),
        mapper=DashboardPayloadMapper(),
        history_days=settings.REALTIME_ALERT_HISTORY_DAYS,
        history_limit=settings.REALTIME_ALERT_HISTORY_LIMIT,
    )


def realtime_consumer() -> RealtimeConsumer:
    return RealtimeConsumer(RealtimeBroadcaster(), dashboard_snapshot_service())
