# Déploiement Docker

Le frontend et l'API ont chacun leur `Dockerfile` et leur `docker-compose.yml`.
Ils se construisent, se déploient et se mettent à jour indépendamment.

## Frontend (`web/`)

```bash
cd web
cp .env.example .env
# GRIDD_API_URL=https://api.gridd.example.org
docker compose build
docker compose up -d
docker compose logs -f
docker compose down
```

| Élément | Valeur |
|---|---|
| Image de base | `node:22-alpine` (LTS), paramétrable par `--build-arg NODE_VERSION=` |
| Construction | `npm ci` (lockfile) puis `npm run build` dans une étape séparée |
| Contenu final | `dist/`, `dist-server/`, `package.json` — ni `node_modules`, ni sources, ni `.env` |
| Utilisateur | `node` (non privilégié) |
| Port | 3000 (publié sur `WEB_PORT`) |
| Santé | `GET /healthz` → `{"status":"ok"}` |
| Démarrage | `node dist-server/index.js` |

Le démarrage ne dépend pas de l'API. L'adresse de l'API est lue **au
démarrage du conteneur** (`GRIDD_API_URL`, `GRIDD_WS_URL`) et servie via
`/env.js` : changer d'environnement (test, production) ne demande qu'un
redémarrage, pas une reconstruction.

> Les valeurs `VITE_*` sont, elles, intégrées au bundle au moment de
> `npm run build`. Ne jamais y placer de secret : tout ce qui est envoyé au
> navigateur est public.

En-têtes de cache : fichiers `assets/*` (noms avec empreinte) mis en cache un
an ; `index.html` et `/env.js` jamais mis en cache, ce qui garantit qu'un
nouveau déploiement est pris en compte immédiatement.

## API (`apps/api/`)

```bash
cd apps/api
cp .env.example .env
# DEBUG=false, DJANGO_SECRET_KEY=<aléatoire>, DB_PASSWORD=<…>,
# ALLOWED_HOSTS=api.gridd.example.org,
# CORS_ALLOWED_ORIGINS=https://gridd.example.org,
# CSRF_TRUSTED_ORIGINS=https://api.gridd.example.org, USE_X_FORWARDED_PROTO=true
docker compose up -d --build                # api, workers, kafka, postgres, redis
docker compose exec api python manage.py createsuperuser
docker compose --profile simulator up -d    # capteurs simulés (facultatif)
docker compose logs -f api workers
```

| Service | Rôle | Notes |
|---|---|---|
| `api` | Daphne (ASGI) : REST, WebSocket, admin | applique les migrations au démarrage (`RUN_MIGRATIONS=true`) ; santé `GET /api/health/` ; publie les commandes d'écriture sur Kafka, donc monte aussi `./secrets` |
| `workers` | `manage.py run_consumers` | modules `ingestion`, `database`, `alarms`, `comfort`, `energy`, `realtime` ; monte `./secrets` (certificat du Kafka GRIDD) |
| `kafka` | Kafka 3.8 (KRaft, un nœud) | bus d'événements ; publié sur 9094 pour le développement hors Docker |
| `simulator` | `manage.py simulate_gridd` | profil `simulator` ; mesures de démonstration |
| `postgres` | PostgreSQL 16 | volume `gridd_postgres_data` ; publié sur 5433 |
| `redis` | Redis 7 | volume `gridd_redis_data` ; publié sur 6379 |

L'image API :

- installe les dépendances dans un environnement virtuel, étape séparée ;
- collecte les fichiers statiques de l'admin à la construction (servis par
  WhiteNoise), avec une clé factice : **aucun secret n'est intégré** ;
- s'exécute sous l'utilisateur `gridd` (uid 10001) ;
- n'exécute plus `migrate` à la construction (la base n'existe pas à ce
  moment-là) : c'est fait au démarrage du service `api` uniquement, pour
  éviter des migrations concurrentes.

### Services externes

Pour une base, un Redis ou un Kafka gérés, renseigner dans `.env` :

```dotenv
CONTAINER_DB_HOST=db.example.internal
CONTAINER_DB_PORT=5432
CONTAINER_REDIS_URL=redis://cache.example.internal:6379/0
CONTAINER_KAFKA_BOOTSTRAP_SERVERS=kafka.example.internal:9092
```

puis `docker compose up -d --no-deps api workers`.

### Kafka

- Les capteurs réels se lisent sur le Kafka GRIDD (`KAFKA_SENSORS_*`, certificat
  dans `./secrets/`) ; les événements internes passent par le bus du Compose
  ou un Kafka géré (`KAFKA_*`).
- `workers` crée les topics internes au démarrage (`KAFKA_AUTO_CREATE_TOPICS`).
  En production, prévoir au moins 3 partitions et un facteur de réplication
  adapté au cluster.
- Montée en charge : dédier un service par module avec
  `run_consumers --module <module>`. `database`, `comfort`, `energy` et `realtime` peuvent être
  dupliqués (Kafka répartit les partitions entre les instances d'un module).
  `ingestion` et `alarms` gardent une vue locale de leur état (historique
  récent des capteurs, état des règles) : les laisser à **une instance** chacun,
  ce qui suffit largement pour quelques centaines de capteurs.
- Le Kafka du Compose conserve les messages tant que le conteneur existe ; ce
  sont des données en transit, la donnée de référence est dans PostgreSQL.

## Production : points d'attention

- **TLS** : terminer HTTPS sur un reverse proxy (Traefik, Nginx…). Côté API,
  `USE_X_FORWARDED_PROTO=true`. `manage.py check --deploy` signale encore
  `SECURE_HSTS_SECONDS` et `SECURE_SSL_REDIRECT` : à régler au niveau du proxy
  ou dans `settings.py` selon l'infrastructure.
- **WebSocket** : le proxy doit relayer `Upgrade`/`Connection` vers
  `/ws/`. L'origine du frontend doit être dans `CORS_ALLOWED_ORIGINS`, sinon
  la connexion est refusée (403).
- **Même domaine** : si un proxy sert le frontend et relaie `/api` et `/ws`
  vers l'API, laisser `GRIDD_API_URL` vide (même origine) ; le CORS devient
  inutile.
- **Accès** : l'API n'a pas d'authentification pour le moment ; ne l'exposer
  que sur un réseau de confiance ou derrière un proxy qui contrôle l'accès.
- **Secrets** : uniquement dans `.env` (non versionné) ou le gestionnaire de
  secrets de l'orchestrateur.
- **Journaux** : les deux applications écrivent sur la sortie standard
  (`docker compose logs`). `LOG_LEVEL` côté API, `LOG_REQUESTS=true` côté
  frontend pour tracer chaque requête.
- **Diagnostic** : `GET /healthz` (frontend), `GET /api/health/` (API : base de
  données, couche temps réel, bus d'événements). `run_consumers --list` affiche
  les abonnements de chaque module. `docker compose ps` affiche l'état de
  santé de chaque service.

## Vérifications effectuées

Docker Hub n'était pas accessible depuis l'environnement de refonte : les
images n'ont pas pu y être construites. Ont été vérifiés :

- `docker compose config` pour les deux fichiers Compose ;
- les étapes de chaque Dockerfile reproduites à l'identique hors conteneur :
  `npm ci` + `npm run build`, puis exécution de `dist-server/` **seul** (sans
  `node_modules`) sous un utilisateur non privilégié, `/healthz`, `/env.js` et
  la commande `HEALTHCHECK` ; installation `pip`, `collectstatic` avec
  `DEBUG=false`, `entrypoint.sh` avec `RUN_MIGRATIONS=true` sur une base
  PostgreSQL vide, Daphne sous un utilisateur non privilégié, contrôle de
  santé, CORS et refus WebSocket d'une origine non autorisée.

Le workflow `.github/workflows/ci.yml` construit les deux images et démarre le
frontend seul : c'est la vérification à surveiller lors du premier envoi.

### Refonte modulaire (bus Kafka)

L'environnement de refonte n'avait ni démon Docker ni accès aux images Kafka :
aucun broker réel n'a pu être démarré. Ont été vérifiés : `docker compose config`
(tous les profils), la suite de tests complète avec le bus mémoire (même code
de modules qu'avec Kafka), le consommateur Kafka et la requête-réponse avec des
clients confluent-kafka simulés, et l'arrêt propre de `run_consumers` quand le
broker est injoignable. Premier démarrage à surveiller : `docker compose logs -f workers`
(création des topics, abonnement de chaque module).
