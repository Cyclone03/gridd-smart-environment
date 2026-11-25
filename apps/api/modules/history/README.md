# Module History

Historique agrégé d'une mesure pour une zone sur une période (moyenne, minimum,
maximum, nombre de mesures et mesures suspectes par créneau, tendance).

## Contrat

| | |
|---|---|
| HTTP | `GET /api/zones/<code>/history/?type=&start=&end=&bucket_minutes=` (aussi `hours`, `date`) — voir `docs/api.md` |
| Kafka | aucun |
| Réglages | `HISTORY_MAX_RANGE_DAYS`, `HISTORY_TARGET_POINTS`, `HISTORY_MAX_POINTS`, `TIME_ZONE` |
| Données lues | `Observation`, `Zone` (schéma du module Database, lecture seule) |

## Structure

```text
core/
  domain/     BucketAggregator, HistoryStatistics
  ports/      HistoryReader
  services/   HistoryService (paramètres → période → agrégation)
adapters/
  persistence/history_repository.py   HistoryReader (ORM Django)
  http/                               contrôleur DRF + urls.py
composition.py                        history_service()
```

## Réutiliser le module

- **Cœur seul** : copier `core/` et `shared/kernel/` (périodes, catalogue des
  mesures), implémenter `HistoryReader` et construire
  `HistoryService(reader=…, period_parser=PeriodParser(...), timezone_provider=…)`.
- **Dans un projet Django** : ajouter `modules.history.apps.HistoryConfig` à
  `INSTALLED_APPS`, inclure `modules.history.adapters.http.urls` et définir les
  réglages ci-dessus. L'adaptateur de persistance lit `modules.database.models`.
