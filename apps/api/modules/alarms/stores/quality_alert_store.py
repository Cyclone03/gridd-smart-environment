class QualityAlertStore:
    """Alertes de qualité actives, par (zone, code), vues par le moteur d'alarmes.

    Même principe que ``RuleStateStore`` : vue locale avec Kafka, lecture en
    base avec le bus mémoire.
    """

    def __init__(self, repository, cache):
        self._repository = repository
        self._cache = cache

    def is_active(self, zone_code, code) -> bool:
        key = (zone_code, code)
        active = self._cache.get(key)
        if active is None:
            active = self._repository.is_active(zone_code, code)
            self._cache.put(key, active)
        return active

    def remember(self, zone_code, code, active):
        self._cache.put((zone_code, code), active)
