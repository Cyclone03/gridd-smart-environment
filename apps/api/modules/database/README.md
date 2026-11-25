# Module Database

**Seul module qui écrit en base.** Il possède le schéma (modèles, migrations,
admin Django) et persiste de façon idempotente les événements des autres
modules, puis publie les faits persistés.

## Contrat

| | |
|---|---|
| Kafka entrée | `DATABASE_SUBSCRIBED_TOPICS` (par défaut `ingestion.observations`, `alarms.events`, `alarms.commands`, `ai_prediction.events`) |
| Kafka sortie | `database.events` : `observation.persisted`, `climate_prediction.persisted`, `weather_snapshot.persisted`, `alerts.changed`, `zones.changed`, `alarm_rule.changed` ; `database.replies` : `command.succeeded`, `command.failed` |
| Schéma | `models/` (label d'application `core`, tables et migrations historiques conservées) |
| Commandes | `python manage.py seed_gridd` (zones GRIDD) ; `python manage.py merge_zone <source> <cible> [--dry-run]` (fusion d'un espace créé par erreur, ex. `node01`) |
| Admin | `/admin/` |

Capteurs : **un par zone et par mesure** (`<zone>-<mesure>`), créés à la
première mesure ou par `seed_gridd` ; le nœud GRIDD d'origine est gardé dans
`metadata.source_node_id`. La migration `0018_sensor_per_zone_and_metric`
convertit les anciens capteurs par nœud (`environmental-node03`…) : chaque
observation est rattachée au capteur de sa propre zone, puis les anciens
capteurs sont supprimés (aucune observation supprimée).

Les autres modules lisent `modules.database.models` **depuis leurs
adaptateurs uniquement** : c'est le schéma partagé, en lecture seule.

## Structure

```text
core/
  ports/      UnitOfWork, ZoneStore, SensorStore, ObservationStore, AlertStore,
              RuleStateStore, AlarmRuleStore, ClimatePredictionStore,
              WeatherSnapshotStore, ObservationPresenter, DatabaseEventsPublisher
  services/   ObservationPersistenceService (lots, références en cache),
              AlertPersistenceService, AlarmRulePersistenceService,
              ClimatePredictionPersistenceService, WeatherSnapshotPersistenceService
              (validation stricte des événements IA)
adapters/
  persistence/   writers ORM, DjangoUnitOfWork (transaction.atomic), ObservationPayloadMapper
  messaging/     PersistenceConsumer (routage, lots, réponses aux commandes),
                 DatabaseEventsProducer, CommandReplyProducer
models/, migrations/, admin/, management/   intégration Django (emplacements imposés)
composition.py   persistence_consumer()
```

## Réutiliser le module

Les règles de persistance (idempotence, validation des prédictions et de la
météo, notifications) sont dans le cœur et ne dépendent que des ports : un
autre stockage s'obtient en fournissant d'autres « stores » et une autre
`UnitOfWork`.
