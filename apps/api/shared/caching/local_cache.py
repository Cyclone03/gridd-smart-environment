from django.conf import settings


class LocalCache:
    """Cache en mémoire du processus, activable.

    Un module qui publie un état (règle d'alarme, historique récent d'un
    capteur) doit en tenir compte dès le message suivant, alors que la base
    n'est mise à jour qu'après le passage par Kafka et le module Database. Il
    garde donc sa propre vue de cet état, initialisée depuis la base.

    Avec le bus mémoire (synchrone), la base est déjà à jour quand l'appel
    revient : le cache est alors désactivé et chaque lecture va en base, ce
    qui permet aussi à plusieurs processus de développement de rester cohérents.
    """

    def __init__(self, enabled, max_entries=10_000):
        self._enabled = enabled
        self._max_entries = max_entries
        self._entries = {}

    @classmethod
    def for_event_bus(cls, max_entries=10_000) -> "LocalCache":
        return cls(enabled=settings.EVENT_BUS == "kafka", max_entries=max_entries)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def get(self, key, default=None):
        return self._entries.get(key, default) if self._enabled else default

    def contains(self, key) -> bool:
        return self._enabled and key in self._entries

    def put(self, key, value):
        if not self._enabled:
            return
        self._entries.pop(key, None)
        self._entries[key] = value
        while len(self._entries) > self._max_entries:
            self._entries.pop(next(iter(self._entries)))

    def discard(self, key):
        self._entries.pop(key, None)

    def discard_where(self, predicate):
        for key in [key for key in self._entries if predicate(key)]:
            self._entries.pop(key, None)
