from modules.alarms.core.domain.refresh_throttle import RefreshThrottle
from modules.alarms.core.domain.rule_state import RuleState


class RuleStateStore:
    """État de chaque (règle, zone), vu par le moteur d'alarmes.

    Le moteur publie chaque nouvel état ; le module Database l'enregistre
    ensuite. Avec Kafka, le moteur garde sa propre vue en mémoire pour que la
    mesure suivante en tienne compte immédiatement (initialisée depuis la base
    au premier passage). Avec le bus mémoire, la base fait foi.

    Avec Kafka, un état inchangé (même statut) et une alerte « en cours » ne
    sont republiés qu'une fois par ``throttle`` (voir ``RefreshThrottle``) :
    tout changement de statut reste publié immédiatement.

    Adaptateur du port ``RuleStates``.
    """

    def __init__(self, repository, cache, throttle=None):
        self._repository = repository
        self._cache = cache
        self._throttle = throttle or RefreshThrottle(enabled=cache.enabled)

    def get(self, rule_id, zone_code) -> RuleState:
        key = (rule_id, zone_code)
        state = self._cache.get(key)
        if state is None:
            state = self._repository.get(rule_id, zone_code) or RuleState.initial()
            self._cache.put(key, state)
        return state

    def remember(self, rule_id, zone_code, state):
        self._cache.put((rule_id, zone_code), state)

    def should_save(self, rule_id, zone_code, state) -> bool:
        """Vrai si l'état doit être publié (statut changé ou intervalle écoulé)."""
        return self._throttle.due(
            ("state", rule_id, zone_code), state.last_observed_at, signature=(state.status, state.pending_since)
        )

    def should_refresh_alert(self, rule_id, zone_code, moment, *, triggered=False) -> bool:
        """Vrai si l'alerte active doit être rafraîchie (déclenchement ou intervalle écoulé)."""
        key = ("alert", rule_id, zone_code)
        if triggered:
            self._throttle.forget(lambda item: item == key)
        return self._throttle.due(key, moment)

    def forget_rule(self, rule_id):
        self._cache.discard_where(lambda key: key[0] == rule_id)
        self._throttle.forget(lambda key: key[1] == rule_id)
