from datetime import timedelta


class RefreshThrottle:
    """Limite la republication d'une information qui ne change pas.

    ``due(key, moment, signature)`` est vrai :
    - à la première occurrence de ``key`` ;
    - si ``signature`` a changé (changement réel : toujours publié) ;
    - si ``interval`` s'est écoulé depuis la dernière publication (horodatage
      de la mesure, pas l'horloge : un rejeu donne le même résultat).

    Pourquoi : une règle toujours déclenchée (ex. « température > 10 °C »)
    republiait l'état et l'alerte à **chaque** mesure ; le module Database
    passait son temps à réécrire les mêmes lignes et les observations
    prenaient du retard.

    Désactivé avec le bus mémoire (la base fait foi, tout est publié).
    """

    def __init__(self, enabled, interval=timedelta(seconds=60), max_entries=10_000):
        self._enabled = enabled
        self._interval = interval
        self._max_entries = max_entries
        self._last = {}

    def due(self, key, moment, signature=None) -> bool:
        if not self._enabled or moment is None:
            return True
        last = self._last.get(key)
        if last is not None:
            last_moment, last_signature = last
            if last_signature == signature and last_moment <= moment < last_moment + self._interval:
                return False
        self._last.pop(key, None)
        self._last[key] = (moment, signature)
        while len(self._last) > self._max_entries:
            self._last.pop(next(iter(self._last)))
        return True

    def forget(self, predicate):
        for key in [key for key in self._last if predicate(key)]:
            self._last.pop(key, None)
