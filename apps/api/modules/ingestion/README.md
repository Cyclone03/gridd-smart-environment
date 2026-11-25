# Module Ingestion

Lit les mesures brutes des capteurs, les rattache à une zone, vérifie leur
cohérence (capteur, unité, type, valeur) et évalue leur qualité, puis publie
les observations validées. Il n'écrit jamais en base.

**Un capteur = une zone + une mesure** (`<zone>-<mesure>`, par exemple
`individual-work-cubicle-01-temperature`, voir `shared.kernel.sensor_identity`).
La zone annoncée par le message fait foi : un nœud GRIDD (`environmental-node03`…)
déplacé ou réétiqueté alimente simplement le capteur de sa nouvelle zone. Le
`node_id` reçu n'est gardé que comme provenance (`metadata.source_node_id`
du capteur, `node_id` de l'événement).

La zone est lue dans les métadonnées du message (`zone` objet ou chaîne,
`zone_id`, `zoneId`…, y compris à la racine du message). Un nœud qui n'annonce
pas sa zone est placé grâce à `GRIDD_NODE_ZONES` (`node01=open-workspace,…`) ;
sinon la mesure est rejetée (« zone absente »). Le `node_id` n'est jamais pris
comme code de zone : cela créait un espace par nœud (node01, node02…).
La caméra d'occupation (`occupancy-camera`) compte les personnes du
laboratoire entier : `occupancy-camera=gridd` (zone « Laboratoire GRIDD »,
créée par `seed_gridd`).

## Contrat

| | |
|---|---|
| Kafka entrée | topics capteurs `KAFKA_SENSOR_TOPICS` (connexion `sensors`, abonnement `ingestion`, départ au bord vivant) |
| Kafka sortie | `observation.validated` sur `KAFKA_TOPICS["ingestion_observations"]`, clé : code de zone |
| Commandes | `python manage.py inspect_kafka` (diagnostic des topics capteurs) ; `python manage.py replay_sensor_topics --since <ISO> [--until <ISO>] [--topic …] [--dry-run]` (rejeu idempotent d'une période) |
| Données lues | capteurs connus, profils de qualité, dernières mesures d'un capteur |
| Format | message capteur et payload : `docs/events.md` |

## Structure

```text
core/
  domain/     SensorReading, ZoneResolver, ReadingValidator, QualityAssessor (+ valeurs)
  ports/      KnownSensorReader, SensorHistory, QualityProfileReader, ObservationPublisher
  services/   IngestionService (zone → cohérence → qualité → publication)
adapters/
  messaging/     SensorReadingConsumer (Kafka), SensorMessageParser, ValidatedObservationProducer,
                 SensorTopicReplayer (rejeu d'une période, sans toucher au groupe temps réel)
  persistence/   repositories ORM + SensorHistoryStore (vue locale, voir docs/architecture.md)
composition.py   ingestion_service(), sensor_reading_consumer()
```

## Réutiliser le module

Le contrôle de qualité (`QualityAssessor`) et la validation sont du Python pur :
`IngestionService` peut être alimenté par une autre source (MQTT, HTTP) et
publier ailleurs en fournissant les quatre ports. Dans un projet Django,
ajouter `modules.ingestion.apps.IngestionConfig` : son abonnement Kafka est
déclaré par `IngestionConfig.subscriptions()` et lancé par `run_consumers`.

## Rejouer une période

```bash
python manage.py replay_sensor_topics --since 2026-11-24T15:00:00-05:00 --dry-run   # combien de messages
python manage.py replay_sensor_topics --since 2026-11-24T15:00:00-05:00             # rejeu
```

Chaque message reçoit le même identifiant qu'en temps réel (dérivé de
topic/partition/offset) : le module Database ignore ceux déjà enregistrés et
n'ajoute que les mesures manquantes. On peut donc relancer sans risque. Les
partitions sont assignées directement et aucun offset n'est validé : le
consommateur temps réel continue normalement. Limite : on ne relit que ce que
le broker GRIDD conserve encore (rétention des topics).
