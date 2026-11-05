class SensorHistoryStore:
    """Historique récent de chaque capteur, vu par l'ingestion.

    La mesure suivante d'un capteur peut arriver avant que le module Database
    ait enregistré la précédente : avec Kafka, l'ingestion garde donc en
    mémoire les dernières mesures qu'elle a validées (initialisées depuis la
    base au premier passage). Avec le bus mémoire, le cache est désactivé et
    la base fait foi.
    """

    LIMIT = 100

    def __init__(self, repository, cache):
        self._repository = repository
        self._cache = cache

    def recent(self, node_id, metric):
        key = (node_id, metric)
        history = self._cache.get(key)
        if history is None:
            history = self._repository.recent(node_id, metric, self.LIMIT)
            self._cache.put(key, history)
        return list(history)

    def record(self, node_id, metric, reading):
        key = (node_id, metric)
        if not self._cache.contains(key):
            return
        history = sorted([reading, *self._cache.get(key)], key=lambda item: item.moment, reverse=True)
        self._cache.put(key, history[: self.LIMIT])
