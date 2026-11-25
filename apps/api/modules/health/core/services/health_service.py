from shared.kernel.timestamps import utc_now


class HealthService:
    """État de santé : base de données, channel layer, bus d'événements et
    fraîcheur des données.

    ``data.stale`` signale qu'aucune mesure n'a été enregistrée depuis
    ``max_data_age_seconds`` (consommateurs arrêtés, en retard ou capteurs
    muets) : le statut passe alors à ``degraded``. Le code HTTP reste 200 tant
    que la base répond — c'est l'état de l'API qui est mesuré, et un
    redémarrage de l'API ne réglerait pas un retard des consommateurs.
    """

    def __init__(self, *, database, freshness, max_data_age_seconds, components=None, clock=utc_now):
        """``components`` : informations statiques ajoutées à la réponse
        (ex. ``{"channel_layer": "RedisChannelLayer", "event_bus": "kafka"}``)."""
        self._database = database
        self._freshness = freshness
        self._max_data_age_seconds = max_data_age_seconds
        self._components = dict(components or {})
        self._clock = clock

    def check(self) -> tuple[dict, bool]:
        database_ok = self._database_ok()
        data = self._data() if database_ok else None
        stale = bool(data and data["stale"])
        return (
            {
                "status": "ok" if database_ok and not stale else "degraded",
                "database": "connected" if database_ok else "error",
                **self._components,
                "data": data,
                "timestamp": self._clock().isoformat(),
            },
            database_ok,
        )

    def _data(self):
        last = self._freshness.last_received_at()
        if last is None:
            return {"last_observation_at": None, "age_seconds": None, "stale": False}
        age = (self._clock() - last).total_seconds()
        return {
            "last_observation_at": last.isoformat(),
            "age_seconds": round(age),
            "stale": age > self._max_data_age_seconds,
        }

    def _database_ok(self) -> bool:
        try:
            return bool(self._database.available())
        except Exception:
            return False
