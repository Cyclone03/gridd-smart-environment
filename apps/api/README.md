# GRIDD — API

Backend Django de GRIDD. Il reçoit les observations (Kafka ou simulateur), les
enregistre dans PostgreSQL, contrôle leur qualité, **évalue les règles
d'alarme**, puis les expose par une API REST et les diffuse en temps réel par
WebSocket (Django Channels + Redis). Il ne sert plus d'interface : le frontend
est l'application séparée [`web/`](../../web/README.md).

## Composants

| Processus | Commande | Rôle |
|---|---|---|
| Serveur ASGI | `daphne config.asgi:application` (ou `manage.py runserver` en développement) | API REST, WebSocket, admin |
| Consumer Kafka | `manage.py consume_kafka` | Ingestion des mesures réelles |
| Simulateur | `manage.py simulate_gridd --interval 30` | Données de test |
| PostgreSQL | — | Stockage |
| Redis | — | Diffusion temps réel entre processus |

## Organisation

```text
config/            settings.py (configuration par variables d'environnement), asgi.py
core/
├── models.py      Zone, Sensor, Observation, Alert, ThresholdProfile, AlarmRule, AlarmRuleState
├── metrics.py     catalogue des mesures : unités, limites physiques, opérateurs
├── services.py    ingestion d'une observation + contrôle de qualité
├── alarm_engine.py évaluation des règles d'alarme (machine à états)
├── history.py     sélection de période et agrégation de l'historique
├── api.py         zones, capteurs, observations, alertes, historique, santé
├── alarm_api.py   CRUD des règles d'alarme
├── auth_api.py    connexion par jeton
├── authentication.py · permissions.py · exceptions.py
├── realtime.py · consumers.py · routing.py   temps réel
├── kafka.py       transformation des messages Kafka
├── management/commands/  consume_kafka, inspect_kafka, seed_gridd, simulate_gridd
├── migrations/
└── tests/         ingestion, API de lecture, moteur d'alarmes, règles, auth, migrations
docker/entrypoint.sh
```

## Installation locale

```bash
cd apps/api
python -m venv .venv
. .venv/bin/activate                    # Windows : .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                    # Windows : Copy-Item .env.example .env
docker compose up -d postgres redis     # PostgreSQL (5433) et Redis (6379)
python manage.py migrate
python manage.py seed_gridd             # zones, capteurs et règles de démonstration
python manage.py createsuperuser
python manage.py runserver              # http://127.0.0.1:8000
```

Dans un second terminal : `python manage.py simulate_gridd --interval 30`
(ou `consume_kafka` pour les données réelles, voir plus bas).

Sans Docker, `DB_ENGINE=sqlite` et `REDIS_URL=` (vide) permettent de démarrer
avec SQLite et une couche temps réel en mémoire. Dans ce cas, le simulateur
s'exécute dans un autre processus et **ne peut pas notifier** le serveur web :
les nouvelles mesures n'apparaissent qu'au rafraîchissement périodique.

## Variables d'environnement

Voir `.env.example` (commenté). Les principales :

| Variable | Défaut | Rôle |
|---|---|---|
| `DJANGO_SECRET_KEY` | — | Obligatoire si `DEBUG=false` |
| `DEBUG` | `false` | Mode développement (API navigable, CORS localhost pour WebSocket) |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Hôtes acceptés |
| `CORS_ALLOWED_ORIGINS` | vide | Origines du frontend autorisées (REST et WebSocket) |
| `CSRF_TRUSTED_ORIGINS` | vide | Origines HTTPS de l'admin Django |
| `USE_X_FORWARDED_PROTO` | `false` | Derrière un proxy TLS |
| `DB_ENGINE`, `DB_*` | `sqlite` | Base de données (`postgres` recommandé) |
| `REDIS_URL` | vide | Couche Channels Redis ; vide = mémoire (un seul processus) |
| `TIME_ZONE` | `America/Toronto` | Fuseau des historiques |
| `AUTH_TOKEN_TTL_HOURS` | `12` | Durée de validité d'un jeton |
| `LOGIN_THROTTLE_RATE` | `10/min` | Limite des tentatives de connexion par IP |
| `HISTORY_MAX_RANGE_DAYS` | `31` | Étendue maximale d'une requête d'historique |
| `HISTORY_TARGET_POINTS` / `HISTORY_MAX_POINTS` | `400` / `3000` | Agrégation automatique / limite d'une granularité imposée |
| `LOG_LEVEL` | `INFO` | Niveau des journaux (sortie standard) |
| `KAFKA_*` | — | Connexion au Kafka GRIDD |

## Comptes et droits

- La consultation (toutes les requêtes `GET`) est publique, comme auparavant.
- Toute écriture exige une authentification par jeton (`POST /api/auth/token/`).
- Les règles d'alarme se gèrent avec les permissions Django
  `core.add_alarmrule`, `core.change_alarmrule`, `core.delete_alarmrule`.
  Le groupe **« Gestionnaires des alarmes »**, créé automatiquement à chaque
  `migrate`, les possède toutes. Un superutilisateur a tous les droits.

Ajouter un utilisateur au groupe : admin Django → Utilisateurs → Groupes, ou

```bash
python manage.py shell -c "from django.contrib.auth.models import User, Group; User.objects.get(username='marie').groups.add(Group.objects.get(name='Gestionnaires des alarmes'))"
```

## Kafka

Placer le certificat CA dans `secrets/gridd-kafka-ca.crt` (exclu de Git et de
l'image), puis dans `.env` : `KAFKA_ENABLED=true`, `KAFKA_USERNAME`,
`KAFKA_PASSWORD` et, hors Docker, `KAFKA_CA_CERT_PATH` (chemin absolu).

```bash
python manage.py inspect_kafka --seconds 30   # lecture sans enregistrement
python manage.py consume_kafka                # ingestion (temps réel)
python manage.py consume_kafka --replay-backlog
```

Le consumer se place à la fin des partitions : plusieurs messages GRIDD n'ont
pas d'horodatage et un retard rejoué apparaîtrait à tort comme actuel. Il doit
être redémarré après une modification du code.

## Docker

```bash
cp .env.example .env          # DJANGO_SECRET_KEY, DB_PASSWORD, CORS_ALLOWED_ORIGINS…
docker compose up -d --build               # api + postgres + redis
docker compose --profile kafka up -d       # + consumer Kafka
docker compose logs -f api
docker compose down                        # conserve les volumes de données
```

- l'image n'exécute **pas** les migrations à la construction ; le service `api`
  les applique au démarrage (`RUN_MIGRATIONS=true`) ;
- utilisateur non privilégié `gridd` (uid 10001), port 8000 ;
- contrôle de santé `GET /api/health/` (503 si la base est indisponible) ;
- PostgreSQL/Redis externes : renseigner `CONTAINER_DB_HOST`,
  `CONTAINER_DB_PORT`, `CONTAINER_REDIS_URL` puis `docker compose up -d --no-deps api`.

Voir [`../../docs/deployment.md`](../../docs/deployment.md).

## Tests

```bash
python manage.py test core
```

54 tests : ingestion et qualité, historique (périodes, validation, fuseaux,
agrégation), alertes, moteur d'alarmes (opérateurs, durée minimale,
hystérésis, portée, messages en retard), API des règles (droits, validation,
cycle de vie), authentification, conversion des anciens seuils. Ils passent
sur SQLite et sur PostgreSQL.

## Adresses utiles

- API : <http://127.0.0.1:8000/api/> (navigable si `DEBUG=true`)
- Santé : <http://127.0.0.1:8000/api/health/>
- Admin : <http://127.0.0.1:8000/admin/>
- WebSocket : `ws://127.0.0.1:8000/ws/dashboard/`
