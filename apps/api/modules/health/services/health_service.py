from django.conf import settings
from django.db import connection
from django.utils import timezone


class HealthService:
    """État de santé du processus : base de données, channel layer, bus d'événements."""

    def check(self) -> tuple[dict, bool]:
        database_ok = self._database_ok()
        return (
            {
                "status": "ok" if database_ok else "degraded",
                "database": "connected" if database_ok else "error",
                "channel_layer": settings.CHANNEL_LAYERS["default"]["BACKEND"].rsplit(".", 1)[-1],
                "event_bus": settings.EVENT_BUS,
                "timestamp": timezone.now().isoformat(),
            },
            database_ok,
        )

    @staticmethod
    def _database_ok() -> bool:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception:
            return False
