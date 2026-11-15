from .refresh_throttle import RefreshThrottle


class QualityAlertStore:
    """Alertes de qualité actives, par (zone, code), vues par le moteur d'alarmes.

    Même principe que ``RuleStateStore`` : vue locale avec Kafka, lecture en
    base avec le bus mémoire. Une alerte déjà active n'est rafraîchie qu'une
    fois par intervalle, sauf changement de statut (suspect → invalide).
    """

    def __init__(self, repository, cache, throttle=None):
        self._repository = repository
        self._cache = cache
        self._throttle = throttle or RefreshThrottle(enabled=cache.enabled)

    def is_active(self, zone_code, code) -> bool:
        key = (zone_code, code)
        active = self._cache.get(key)
        if active is None:
            active = self._repository.is_active(zone_code, code)
            self._cache.put(key, active)
        return active

    def remember(self, zone_code, code, active):
        self._cache.put((zone_code, code), active)
        if not active:
            self._throttle.forget(lambda key: key == (zone_code, code))

    def should_refresh(self, zone_code, code, status, moment) -> bool:
        """Faux si l'alerte est active, de même statut, et rafraîchie récemment."""
        if not self.is_active(zone_code, code):
            self._throttle.forget(lambda key: key == (zone_code, code))
        return self._throttle.due((zone_code, code), moment, signature=status)
