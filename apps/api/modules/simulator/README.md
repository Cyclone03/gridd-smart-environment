# Module Simulator

Joue le rôle des capteurs pour les démonstrations : publie des mesures au
format capteur GRIDD (marche aléatoire bornée par type de mesure) qui suivent
exactement le chemin des mesures réelles.

## Contrat

| | |
|---|---|
| Commande | `python manage.py simulate_gridd [--interval 30] [--iterations 0]` |
| Kafka | publie sur les topics capteurs (`KAFKA_SENSOR_TOPICS`, connexion `sensors`), clé : `node_id` |
| Données lues | capteurs actifs et leur dernière valeur |

## Structure

```text
core/
  domain/     SimulatedSensor, ValueGenerator
  ports/      SensorSource, ReadingPublisher
  services/   SimulatorService (start, tick)
adapters/
  persistence/simulated_sensor_repository.py   SensorSource
  messaging/sensor_topic_publisher.py          ReadingPublisher (topic capteur du type)
composition.py                                 simulator_service()
management/commands/simulate_gridd.py
```

## Réutiliser le module

`SimulatorService` accepte n'importe quelle source de capteurs et n'importe
quel `ReadingPublisher` (MQTT, HTTP, fichier…) ; `clock` et `generator` sont
injectables pour des simulations reproductibles.
