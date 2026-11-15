from django.conf import settings
from django.db import connection
from django.utils import timezone

from modules.database.models import Observation


class HealthService:
    """État de santé : base de données, channel layer, bus d'événements et
    fraîcheur des données.

    ``data.stale`` signale qu'aucune mesure n'a été enregistrée depuis
    ``HEALTH_MAX_DATA_AGE_SECONDS`` (consommateurs arrêtés, en retard ou
    capteurs muets) : le statut passe alors à ``degraded``. Le code HTTP reste
    200 tant que la base répond — c'est l'état de l'API qui est mesuré, et un
    redémarrage de l'API ne réglerait pas un retard des consommateurs.
    """

    def check(self) -> tuple[dict, bool]:
        database_ok = self._database_ok()
        data = self._data() if database_ok else None
        stale = bool(data and data["stale"])
        return (
            {
                "status": "ok" if database_ok and not stale else "degraded",
                "database": "connected" if database_ok else "error",
                "channel_layer": settings.CHANNEL_LAYERS["default"]["BACKEND"].rsplit(".", 1)[-1],
                "event_bus": settings.EVENT_BUS,
                "data": data,
                "timestamp": timezone.now().isoformat(),
            },
            database_ok,
        )

    @staticmethod
    def _data():
        # Dernière ligne insérée (index de clé primaire : pas de tri sur toute la table).
        last = Observation.objects.order_by("-pk").values_list("received_at", flat=True).first()
        if last is None:
            return {"last_observation_at": None, "age_seconds": None, "stale": False}
        age = (timezone.now() - last).total_seconds()
        return {
            "last_observation_at": last.isoformat(),
            "age_seconds": round(age),
            "stale": age > settings.HEALTH_MAX_DATA_AGE_SECONDS,
        }

    @staticmethod
    def _database_ok() -> bool:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception:
            return False
