# GRIDD — API

Backend Django de GRIDD, organisé en **modules autonomes qui ne communiquent
que par Kafka**. Les mesures des capteurs sont validées et qualifiées
(`ingestion`), enregistrées par le seul module autorisé à écrire en base
(`database`), puis exploitées par le moteur d'alarmes (`alarms`). Tout est
diffusé en temps réel (`realtime`). L'API REST et les WebSocket servent le frontend
séparé [`apps/web/`](../web/README.md).

Architecture détaillée : [`docs/architecture.md`](../../docs/architecture.md).
Topics et événements : [`docs/events.md`](../../docs/events.md).

## Processus

| Processus | Commande | Rôle |
|---|---|---|
| Serveur ASGI | `daphne config.asgi:application` (ou `manage.py runserver`) | API REST, WebSocket, admin |
| Consommateurs | `manage.py run_consumers [--module …]` | Modules `ingestion`, `database`, `alarms`, `realtime` (avec `EVENT_BUS=kafka`) |
| Simulateur | `manage.py simulate_gridd --interval 30` | Mesures de démonstration sur les topics capteurs |
| Kafka | — | Bus d'événements entre modules |
| PostgreSQL | — | Stockage (écrit uniquement par `database`) |
| Redis | — | Diffusion temps réel entre processus |

## Organisation

```text
config/                 settings.py, urls.py (routage HTTP), asgi.py (routage WebSocket)
shared/                 noyau commun — pas un module métier
├── messaging/          enveloppe d'événement, bus Kafka / mémoire, consommateurs, requête-réponse
├── contracts/          noms des topics, types d'événements
├── metrics/            catalogue des mesures et opérateurs
├── periods/            périodes d'analyse (start/end, granularité, créneaux)
├── http/               format d'erreur, permissions de lecture publique
├── caching/            vue locale activable (cohérence avec Kafka)
└── management/commands/run_consumers.py
modules/
├── database/           models/, migrations/, admin/, writers/, services/, consumers/, producers/
├── ingestion/          parsers/, domain/ (validation, qualité), repositories/, stores/, services/, consumers/, producers/
├── alarms/             controllers/, serializers/, services/, domain/ (moteur), repositories/, stores/, consumers/, producers/
├── observations/       zones, capteurs, mesures (lecture)
├── history/            historique agrégé (lecture)
├── realtime/           WebSocket et diffusion
├── health/             contrôle de santé
└── simulator/          capteurs simulés
tests/                  règles d'architecture, routage, utilitaires de test
docker/entrypoint.sh
```

Règles (vérifiées par `tests/test_architecture.py`) : une classe par fichier,
aucun import entre modules (hors `shared` et lecture de
`modules.database.models`), aucune écriture en base hors de `database`,
contrôleurs sans accès aux données.

## Installation locale

PostgreSQL et Redis doivent être démarrés séparément et leurs adresses
configurées dans `.env`. Le fichier Compose de l'API ne fournit pas ces
dépendances : il ne déclare que l'API et le consommateur Kafka.

```bash
cd apps/api
python -m venv .venv
. .venv/bin/activate                    # Windows : .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                    # Windows : Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_gridd             # zones, capteurs et règles de démonstration
python manage.py createsuperuser
python manage.py runserver              # http://127.0.0.1:8000
```

`.env.example` utilise `EVENT_BUS=memory` : sans Kafka, chaque processus
exécute toute la chaîne. Dans un second terminal,
`python manage.py simulate_gridd --interval 30` produit des mesures, qui
traversent ingestion → database → alarms → realtime dans ce processus et
arrivent au navigateur par Redis.

### Avec Kafka (comme en production)

Le fichier Compose ne démarre pas Kafka, PostgreSQL ni Redis. Ces services
doivent être accessibles séparément. `run_consumers` démarre les groupes
configurés et valide les offsets après traitement; vérifier `EVENT_BUS=kafka`,
le broker et les groupes avant de le lancer sur un environnement partagé.

```bash
# .env : EVENT_BUS=kafka
python manage.py runserver                  # terminal 1 : API
python manage.py run_consumers              # terminal 2 : modules
python manage.py simulate_gridd             # terminal 3 : capteurs simulés
```

Sans Docker du tout : `DB_ENGINE=sqlite`, `REDIS_URL=` (vide), `EVENT_BUS=memory`.
Le temps réel ne fonctionne alors qu'à l'intérieur d'un même processus.

## Variables d'environnement

Voir `.env.example` (commenté). Les principales :

| Variable | Défaut | Rôle |
|---|---|---|
| `DJANGO_SECRET_KEY` | — | Obligatoire si `DEBUG=false` |
| `DEBUG` | `false` | Mode développement |
| `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | — | Hôtes et origines autorisés |
| `DB_ENGINE`, `DB_*` | `sqlite` | Base de données (`postgres` recommandé) |
| `REDIS_URL` | vide | Couche Channels Redis ; vide = mémoire (un seul processus) |
| `EVENT_BUS` | `memory` | `kafka` en production |
| `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_SECURITY_PROTOCOL`, `KAFKA_USERNAME`… | `localhost:9092`, `PLAINTEXT` | Bus interne |
| `KAFKA_SENSORS_*` | = bus interne | Cluster des topics capteurs (Kafka GRIDD) |
| `KAFKA_TOPIC_*` | voir `docs/events.md` | Noms des topics |
| `DATABASE_SUBSCRIBED_TOPICS` | topics d'ingestion et d'alarmes | Topics persistés par `database` |
| `KAFKA_CONSUMER_GROUP_PREFIX` | `gridd-backend` | Consumer group : `<préfixe>.<module>` |
| `KAFKA_COMMAND_TIMEOUT_SECONDS` | `10` | Attente d'une réponse aux commandes de règles ; au-delà : 503 |
| `KAFKA_MAX_ATTEMPTS`, `KAFKA_RETRY_DELAY_SECONDS` | `5`, `2` | Nouvelles tentatives sur erreur transitoire |
| `KAFKA_AUTO_CREATE_TOPICS` | `true` | Création des topics internes au démarrage des consommateurs |
| `HISTORY_MAX_RANGE_DAYS`, `HISTORY_TARGET_POINTS`, `HISTORY_MAX_POINTS` | `31`, `400`, `3000` | Historique |

## Accès

Pas d'authentification pour le moment : lectures et écritures sont ouvertes.
En production, restreindre l'accès à l'API par le réseau ou un proxy. L'admin
Django (`/admin/`, compte créé avec `createsuperuser`) reste disponible pour
la maintenance des données.

## Capteurs réels (Kafka GRIDD)

Placer le certificat CA dans `secrets/gridd-kafka-ca.crt` (exclu de Git et de
l'image), puis dans `.env` : `KAFKA_SENSORS_BOOTSTRAP_SERVERS=kafka.gridd-dt.ca:9096`,
`KAFKA_SENSORS_SECURITY_PROTOCOL=SASL_SSL`, `KAFKA_SENSORS_USERNAME`,
`KAFKA_SENSORS_PASSWORD` et, hors Docker, `KAFKA_SENSORS_CA_CERT_PATH`.

```bash
python manage.py inspect_kafka --seconds 30           # lecture sans traitement
python manage.py run_consumers                        # tous les modules
python manage.py run_consumers --module ingestion --replay-backlog
python manage.py run_consumers --list                 # abonnements de chaque module
```

`ingestion` se place à la fin des partitions capteurs (plusieurs messages
GRIDD n'ont pas d'horodatage : un retard rejoué apparaîtrait à tort comme
actuel). Les topics internes, eux, sont toujours lus intégralement. Ne pas
lancer le simulateur quand les topics capteurs visent le Kafka GRIDD.

## Docker

```bash
cp .env.example .env          # DJANGO_SECRET_KEY, DB_PASSWORD, CORS_ALLOWED_ORIGINS…
docker compose config --quiet
docker compose build api
docker compose up -d api
# Démarrer le consommateur seulement après vérification des groupes Kafka.
docker compose up -d kafka-consumer
docker compose logs -f api kafka-consumer
docker compose down
```

Le Compose API ne contient ni PostgreSQL, ni Redis, ni broker Kafka. Les
adresses dans `.env` doivent être joignables depuis les conteneurs. Le
certificat Kafka, lorsqu'il est requis, doit être placé dans
`secrets/gridd-kafka-ca.crt`. Les migrations ne sont pas exécutées
automatiquement par ce Compose.

Voir [`../../docs/deployment.md`](../../docs/deployment.md).

## Tests

```bash
python manage.py test
```

La suite utilise le bus mémoire (aucun Kafka requis) et vérifie la chaîne
capteur → ingestion → database → alarms → realtime, la qualité des données,
les API, l'historique, l'idempotence du module Database, le consommateur Kafka,
les migrations et les règles d'architecture. Les tables et migrations
historiques des évaluations de confort et estimations énergétiques sont
conservées pour préserver les données existantes; aucun traitement actif ne
les alimente.

## Adresses utiles

- API : <http://127.0.0.1:8000/api/>
- Santé : <http://127.0.0.1:8000/api/health/> (indique aussi `event_bus`)
- Admin : <http://127.0.0.1:8000/admin/>
- WebSocket : `ws://127.0.0.1:8000/ws/dashboard/`
