# Module Ingestion

Lit les mesures brutes des capteurs, les rattache à une zone, vérifie leur
cohérence (capteur, unité, type, valeur) et évalue leur qualité, puis publie
les observations validées. Il n'écrit jamais en base.

## Contrat

| | |
|---|---|
| Kafka entrée | topics capteurs `KAFKA_SENSOR_TOPICS` (connexion `sensors`, abonnement `ingestion`, départ au bord vivant) |
| Kafka sortie | `observation.validated` sur `KAFKA_TOPICS["ingestion_observations"]`, clé : code de zone |
| Commande | `python manage.py inspect_kafka` (diagnostic des topics capteurs) |
| Données lues | capteurs connus, profils de qualité, dernières mesures d'un capteur |
| Format | message capteur et payload : `docs/events.md` |

## Structure

```text
core/
  domain/     SensorReading, ZoneResolver, ReadingValidator, QualityAssessor (+ valeurs)
  ports/      KnownSensorReader, SensorHistory, QualityProfileReader, ObservationPublisher
  services/   IngestionService (zone → cohérence → qualité → publication)
adapters/
  messaging/     SensorReadingConsumer (Kafka), SensorMessageParser, ValidatedObservationProducer
  persistence/   repositories ORM + SensorHistoryStore (vue locale, voir docs/architecture.md)
composition.py   ingestion_service(), sensor_reading_consumer()
```

## Réutiliser le module

Le contrôle de qualité (`QualityAssessor`) et la validation sont du Python pur :
`IngestionService` peut être alimenté par une autre source (MQTT, HTTP) et
publier ailleurs en fournissant les quatre ports. Dans un projet Django,
ajouter `modules.ingestion.apps.IngestionConfig` : son abonnement Kafka est
déclaré par `IngestionConfig.subscriptions()` et lancé par `run_consumers`.
