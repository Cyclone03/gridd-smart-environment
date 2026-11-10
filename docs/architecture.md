# Architecture

## Vue d'ensemble

GRIDD est composé de deux applications déployées séparément : l'API
(`apps/api`) et le frontend (`web`). Le backend est organisé en **modules
autonomes** qui ne communiquent **que par Kafka**.

```text
                         ┌───────────────────────────┐
                         │         Capteurs          │   (ou simulateur)
                         └─────────────┬─────────────┘
                                       │ topics capteurs gridd.obs.*
┌──────────────────────────────────────▼──────────────────────────────────────────┐
│                                     Kafka                                       │
│  ingestion.observations · alarms.* · database.*                              │
└────┬──────▲──────────┬──────▲─────────────┬──────▲──────────┬──────▲────────────┘
     │      │          │      │             │      │          │      │
┌────┼──────┼──────────┼──────┼─────────────┼──────┼──────────┼──────┼────────────┐
│    ▼      │          ▼      │             ▼      │          ▼      │  Backend   │
│ ┌─────────┴──┐ ┌─────────────┴──┐ ┌────────────────┴─┐ ┌─────────────┴──┐         │
│ │ ingestion  │ │   database     │ │     alarms       │ │   realtime     │         │
│ │ (capteurs) │ │ (seul à écrire)│ │ règles, alertes  │ │ WebSocket      │         │
│ └────────────┘ └───────┬────────┘ └────────┬─────────┘ └───────┬────────┘         │
│                        │ PostgreSQL        │                    │                 │
│          observations · history · health                                     │
│ ┌──────────────────────┴───────────────────┴────────────────────┴───────────────┐ │
│ │              Routage : config/urls.py (REST) · config/asgi.py (WS)            │ │
│ └───────────────────────────────────────▲───────────────────────────────────────┘ │
└─────────────────────────────────────────┼─────────────────────────────────────────┘
                                          │ HTTPS + WSS
                         ┌────────────────┴──────────┐
                         │      Frontend (web/)      │
                         └───────────────────────────┘
```

## Analyse de l'existant et décisions

Avant la refonte, une seule application Django `core` réunissait modèles, API
REST, ingestion Kafka, moteur d'alarmes, temps réel et authentification.
L'ingestion était un appel synchrone (`consume_kafka` → `services.ingest_observation`)
qui, dans une même transaction, créait zones et capteurs, contrôlait la
qualité, écrivait l'observation, évaluait les règles, écrivait les alertes et
diffusait. Kafka n'était utilisé qu'en entrée et tous les composants
écrivaient directement en base.

| Élément existant | Décision | Destination |
|---|---|---|
| Modèles et migrations `core` | **Conservés** à l'identique (label `core` gardé : tables, historique des migrations et permissions `core.*_alarmrule` inchangés). Ajout d'`Observation.event_id` (idempotence). | `modules/database/models/`, `modules/database/migrations/` |
| Catalogue des mesures (`metrics.py`) | **Déplacé** dans le noyau partagé, découpé en classes | `shared/metrics/` |
| `services.ingest_observation` (ingestion + qualité + alarmes + diffusion) | **Refactorisé** : ingestion et qualité dans `ingestion`, persistance dans `database`, alarmes dans `alarms`, diffusion dans `realtime`, reliés par Kafka | 4 modules |
| `kafka.py`, `consume_kafka` | **Supprimés**, remplacés par `SensorMessageParser` (même format accepté) et `run_consumers` (tous les modules) | `modules/ingestion/`, `shared/messaging/` |
| `alarm_engine.py` | **Conservé** dans sa logique, découpé : évaluation pure (`ConditionEvaluator`, `AlarmStateMachine`, `RuleChangePolicy`) et services qui publient les décisions | `modules/alarms/` |
| `history.py`, vue `zone_history` | **Conservés**, découpés : `PeriodParser`, `BucketAggregator`, `HistoryStatistics`, service, contrôleur | `modules/history/` |
| `api.py`, `alarm_api.py` | **Refactorisés** en contrôleurs minces + services + repositories, contrat REST identique | `observations`, `alarms`, `health` |
| `auth_api.py`, jetons, permissions | **Supprimés** (pas d'authentification pour le moment) ; page de connexion retirée du frontend | — |
| Confort thermique et estimation énergétique | Retirés des services actifs; schéma historique conservé pour préserver les données | — |
| Validation métier des règles dans le serializer | **Déplacée** dans `AlarmRuleValidator` (logique pure) | `modules/alarms/domain/` |
| `realtime.py`, `consumers.py` (Channels) | **Déplacés** ; la diffusion part désormais des faits persistés | `modules/realtime/` |
| Simulateur (écrivait en base) | **Refactorisé** : publie sur les topics capteurs comme un vrai capteur | `modules/simulator/` |
| Admin Django | **Conservé**, une classe par fichier | `modules/database/admin/` |
| Frontend `web/` | Déployé séparément; les routes confort thermique et énergie ont été retirées | — |

## Modules

| Module | Responsabilité | Kafka : lit → publie | API |
|---|---|---|---|
| `ingestion` | Lire les mesures capteurs, valider (capteur, unité, valeur), contrôler la qualité | capteurs → `ingestion.observations` | — |
| `database` | **Seul module qui écrit en base** : observations, zones, capteurs, alertes, états et règles | `DATABASE_SUBSCRIBED_TOPICS` → `database.events`, `database.replies` | admin Django |
| `alarms` | Règles d'alarme (CRUD), évaluation, alertes de qualité, consultation des alertes | `database.events` → `alarms.events`, `alarms.commands` | `/api/alarm-rules/`, `/api/alerts/` |
| `realtime` | Diffuser aux navigateurs les faits persistés (mesures, alertes) | `database.events` → (WebSocket) | `/ws/dashboard/`, `/ws/zones/<code>/` |
| `observations` | Consulter zones, capteurs et mesures | — | `/api/zones/`, `/api/sensors/`, `/api/observations/` |
| `history` | Historique agrégé sur une période | — | `/api/zones/<code>/history/` |
| `health` | Santé du processus | — | `/api/health/` |
| `simulator` | Mesures de démonstration | → topics capteurs | — |

`shared/` n'est pas un module : c'est le noyau commun (messagerie, contrats
d'événements, catalogue des mesures, périodes d'analyse, format d'erreur HTTP).

### Organisation interne d'un module

Chaque module ne contient que les dossiers dont il a besoin :

```text
modules/<module>/
├── apps.py          configuration Django + abonnements Kafka du module
├── urls.py          routes HTTP du module
├── controllers/     endpoints : lisent la requête, délèguent au service, sérialisent
├── services/        logique métier et communication Kafka (producteurs, commandes)
├── consumers/       point d'entrée Kafka : décode et transmet au service
├── producers/       publication dans les topics de sortie du module
├── domain/          logique pure (sans base, sans Kafka, sans HTTP)
├── repositories/    lectures en base (lecture seule)
├── stores/          vue locale d'un état publié (voir « Cohérence »)
├── serializers/     forme des données HTTP
└── tests/
```

Le module `database` remplace `repositories/` par `writers/` (écritures) et
ajoute `models/`, `migrations/`, `admin/`, `provisioning/`.

## Flux

### Mesure capteur

1. `ingestion` lit un topic capteur, valide la mesure, évalue sa qualité et
   publie `observation.validated` (clé : zone).
2. `database` crée au besoin la zone et le capteur, enregistre l'observation
   (idempotent grâce à `event_id`) puis publie `observation.persisted`.
3. `alarms` met à jour les alertes de qualité et évalue les règles ; il publie
   ses décisions (`alert.raised`, `alert.resolved`, `alarm_state.saved`).
4. `database` les enregistre et publie `alerts.changed` si la liste des
   alertes actives a changé.
5. `realtime` relaie les mesures et alertes persistées aux navigateurs.

### Requête de lecture (frontend)

`Controller` → `Service` → `Repository` (lecture seule) → réponse. Aucune
écriture, aucune logique métier dans le contrôleur.

### Requête d'écriture (frontend)

Exemple : `POST /api/alarm-rules/`.

1. Le contrôleur valide la forme des données (serializer + `AlarmRuleValidator`).
2. Le service envoie la commande `alarm_rule.create` sur `alarms.commands`
   avec un `correlation_id` et attend la réponse (`CommandGateway`).
3. `database` enregistre la règle, publie `alarm_rule.changed`, puis répond
   `command.succeeded` sur `database.replies`.
4. Le service relit la règle enregistrée ; le contrôleur la renvoie (201).

Sans réponse dans `KAFKA_COMMAND_TIMEOUT_SECONDS`, l'API répond 503 ; une
commande refusée donne 400 ou 404. Les effets sur les alertes en cours
(règle désactivée, modifiée, supprimée) sont décidés par `alarms` à la
réception de `alarm_rule.changed`.

## Règles de conception (vérifiées par les tests)

`tests/test_architecture.py` échoue si :

- un fichier contient plus d'une classe ;
- un module importe un autre module (seuls `shared` et la lecture du schéma
  `modules.database.models` sont autorisés) ;
- un module autre que `database` écrit en base (`save`, `create`, `update`,
  `delete`…) ;
- un contrôleur importe un repository, un writer ou `django.db`.

## Bus d'événements

| `EVENT_BUS` | Usage | Fonctionnement |
|---|---|---|
| `kafka` | production, Docker | publication sur Kafka ; `manage.py run_consumers` exécute les consommateurs (un thread et un consumer group `<préfixe>.<module>` par module) |
| `memory` | tests, développement sans Kafka | bus synchrone en mémoire : tous les abonnements sont branchés dans le processus qui publie |

Les modules ne voient que des abstractions (`EventPublisher`, `EventHandler`,
`CommandGateway`) : passer de l'un à l'autre ne change aucun module.

Livraison **au moins une fois** : un consommateur valide l'offset après
traitement ; une erreur transitoire est réessayée (`KAFKA_MAX_ATTEMPTS`), un
message invalide est journalisé puis ignoré. La persistance est idempotente
(`event_id` des observations, une seule alerte active par zone et code).

### Cohérence

Avec Kafka, la base n'est mise à jour qu'après le passage par le module
`database`. Un module qui dépend de son propre état publié (état des règles
pour `alarms`, historique récent d'un capteur pour `ingestion`) garde donc une
vue locale (`stores/`), initialisée depuis la base et alimentée par ses propres
décisions. Les messages d'une même zone partagent la même clé de partition et
sont traités dans l'ordre. Avec le bus mémoire, la base est déjà à jour et
cette vue locale est désactivée.

Conséquences :

- `ingestion` et `alarms` tournent chacun en **une seule instance** (un
  événement `alarm_rule.changed` n'est remis qu'à une instance du groupe) ;
- avec Kafka, la réponse à une modification de règle est renvoyée dès que la
  règle est enregistrée ; la clôture des alertes en cours suit quelques
  millisecondes plus tard et le frontend en est notifié par `alerts.changed`.

## Décisions conservées de la version précédente

- **Une alerte = un épisode** (`created_at` → `resolved_at`, `resolution`).
- **Les mesures invalides n'alimentent pas les règles** : elles déclenchent
  déjà une alerte de qualité.
- **Pas d'authentification pour le moment** : l'API et l'interface sont ouvertes ; à protéger par le réseau ou un proxy.

## Frontend (`web`)

Inchangé par cette refonte. Voir [`web/README.md`](../web/README.md) :
`View` → `composable` → `service` → `requests/httpClient` → API.

## Évolutivité

- **Nouveau paramètre mesuré** : choix dans `Sensor.SensorType`, entrée dans
  `shared/metrics/metric_catalog.py`, topic capteur dans la configuration ;
  côté frontend, `constants/metrics.ts`.
- **Nouvel opérateur** : `shared/metrics/operator.py` et
  `modules/alarms/domain/condition_evaluator.py`.
- **Nouveau module** : dossier `modules/<nom>/` avec son `apps.py`
  (`ModuleConfig`, abonnements dans `subscriptions()`), inscription dans
  `INSTALLED_APPS`, routes ajoutées à `config/urls.py`. S'il doit écrire en
  base, il publie un événement et `database` reçoit un writer.
- **Séparer les consommateurs** : `run_consumers --module database`, etc.,
  un processus par module si la charge le demande (voir « Cohérence »).
