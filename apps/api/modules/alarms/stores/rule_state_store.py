from modules.alarms.domain.rule_state import RuleState


class RuleStateStore:
    """État de chaque (règle, zone), vu par le moteur d'alarmes.

    Le moteur publie chaque nouvel état ; le module Database l'enregistre
    ensuite. Avec Kafka, le moteur garde sa propre vue en mémoire pour que la
    mesure suivante en tienne compte immédiatement (initialisée depuis la base
    au premier passage). Avec le bus mémoire, la base fait foi.
    """

    def __init__(self, repository, cache):
        self._repository = repository
        self._cache = cache

    def get(self, rule_id, zone_code) -> RuleState:
        key = (rule_id, zone_code)
        state = self._cache.get(key)
        if state is None:
            state = self._repository.get(rule_id, zone_code) or RuleState.initial()
            self._cache.put(key, state)
        return state

    def remember(self, rule_id, zone_code, state):
        self._cache.put((rule_id, zone_code), state)

    def forget_rule(self, rule_id):
        self._cache.discard_where(lambda key: key[0] == rule_id)
