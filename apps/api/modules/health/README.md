# Module Health

Contrôle de santé de l'API pour Docker et la supervision : base de données,
channel layer, bus d'événements et fraîcheur des données.

## Contrat

| | |
|---|---|
| HTTP | `GET /api/health/` → 200 si la base répond, 503 sinon ; `status: degraded` si aucune mesure depuis `HEALTH_MAX_DATA_AGE_SECONDS` |
| Kafka | aucun |
| Réglages | `HEALTH_MAX_DATA_AGE_SECONDS`, `CHANNEL_LAYERS`, `EVENT_BUS` |

## Structure

```text
core/
  ports/      DatabaseProbe, DataFreshnessReader
  services/   HealthService (statut, âge de la dernière mesure)
adapters/
  persistence/django_database_probe.py              DatabaseProbe (SELECT 1)
  persistence/observation_freshness_repository.py   DataFreshnessReader
  http/                                             contrôleur + urls.py
composition.py                                      health_service()
```

## Réutiliser le module

`HealthService` ne dépend que de ses deux ports, du délai maximal et d'un
dictionnaire `components` libre (informations ajoutées telles quelles à la
réponse) : il convient à tout service qui doit exposer « base joignable +
données récentes ».
