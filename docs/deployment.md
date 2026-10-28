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
docker compose up -d --build
docker compose exec api python manage.py createsuperuser
docker compose --profile kafka up -d        # consumer Kafka (certificat dans ./secrets/)
docker compose logs -f api
```

| Service | Rôle | Notes |
|---|---|---|
| `api` | Daphne (ASGI) : REST, WebSocket, admin | applique les migrations au démarrage (`RUN_MIGRATIONS=true`) ; santé `GET /api/health/` |
| `kafka-consumer` | `manage.py consume_kafka` | profil `kafka` ; monte `./secrets` en lecture seule |
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

Pour une base ou un Redis gérés, renseigner dans `.env` :

```dotenv
CONTAINER_DB_HOST=db.example.internal
CONTAINER_DB_PORT=5432
CONTAINER_REDIS_URL=redis://cache.example.internal:6379/0
```

puis `docker compose up -d --no-deps api`.

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
- **Secrets** : uniquement dans `.env` (non versionné) ou le gestionnaire de
  secrets de l'orchestrateur.
- **Journaux** : les deux applications écrivent sur la sortie standard
  (`docker compose logs`). `LOG_LEVEL` côté API, `LOG_REQUESTS=true` côté
  frontend pour tracer chaque requête.
- **Diagnostic** : `GET /healthz` (frontend), `GET /api/health/` (API : base de
  données et type de couche temps réel). `docker compose ps` affiche l'état de
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
