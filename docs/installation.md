# Installation locale

Deux terminaux suffisent : un pour l'API, un pour le frontend. Les deux
applications s'installent indépendamment.

## Prérequis

- Python 3.12 ou 3.13 ;
- Node.js 20.19+ ou 22.12+ et npm ;
- Docker avec Docker Compose (pour PostgreSQL et Redis) ;
- accès au Kafka GRIDD et certificat CA, uniquement pour les données réelles.

| Service | Port | Remarque |
|---|---:|---|
| API Django | 8000 | REST, WebSocket, admin |
| PostgreSQL | 5433 | publié par `apps/api/docker-compose.yml` |
| Redis | 6379 | publié par `apps/api/docker-compose.yml` |
| Vite (développement) | 5173 | relaie `/api` et `/ws` vers l'API |
| Frontend Node (production) | 3000 | `npm start` ou Docker |

## 1. API

```bash
cd apps/api
python -m venv .venv
. .venv/bin/activate                 # Windows : .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                 # Windows : Copy-Item .env.example .env
```

`.env.example` contient des valeurs de développement fonctionnelles
(`DEBUG=true`, PostgreSQL sur 5433, Redis sur 6379). Démarrer les services :

```bash
docker compose up -d postgres redis
python manage.py migrate
python manage.py seed_gridd          # 6 zones, capteurs et 4 règles d'alarme de démonstration
python manage.py createsuperuser
python manage.py runserver           # http://127.0.0.1:8000
```

`seed_gridd` ne crée des règles que si aucune n'existe : sur une base déjà
migrée, les anciens seuils ont été convertis en règles (voir
[`alarms.md`](alarms.md#migration-des-anciens-seuils)).

Données simulées, dans un second terminal :

```bash
cd apps/api && . .venv/bin/activate
python manage.py simulate_gridd --interval 30
```

Données réelles : voir la section Kafka de [`apps/api/README.md`](../apps/api/README.md#kafka).
Ne pas lancer le simulateur et Kafka en même temps, sauf mélange volontaire.

### Sans Docker

```dotenv
DB_ENGINE=sqlite
REDIS_URL=
```

L'API fonctionne alors avec SQLite et une couche temps réel en mémoire. Les
mesures produites par un autre processus (simulateur, Kafka) ne sont pas
diffusées en direct ; le frontend les affiche à son rafraîchissement
périodique (60 s).

## 2. Frontend

```bash
cd web
npm ci
npm run dev                          # http://localhost:5173
```

Vite relaie `/api` et `/ws` vers `VITE_DEV_API_PROXY` (défaut
`http://127.0.0.1:8000`) : aucune configuration CORS n'est nécessaire en
développement. Pour viser une autre API, créer `web/.env` :

```dotenv
VITE_DEV_API_PROXY=https://api-gridd.example.org
```

Tester le build de production en local :

```bash
npm run build
GRIDD_API_URL=http://localhost:8000 npm start      # http://localhost:3000
```

L'origine `http://localhost:3000` doit alors figurer dans
`CORS_ALLOWED_ORIGINS` de l'API (c'est le cas dans `.env.example`).

## 3. Donner les droits de gestion des alarmes

La consultation est libre. Pour créer ou modifier des règles, se connecter
avec le superutilisateur, ou ajouter un compte au groupe
« Gestionnaires des alarmes » (admin Django → Utilisateurs).

## 4. Vérifier

```bash
cd apps/api && python manage.py check && python manage.py test core
cd web && npm run typecheck && npm test && npm run build
```

## Dépannage

| Symptôme | Piste |
|---|---|
| Badge « WebSocket interrompu » | API arrêtée, Redis arrêté, ou origine du frontend absente de `CORS_ALLOWED_ORIGINS` (refus 403 du WebSocket). |
| `InvalidChannelLayerError … channels_redis` | Dépendances installées dans un autre environnement Python : `pip install -r requirements.txt`. |
| « Impossible de joindre l'API GRIDD » | Mauvaise `GRIDD_API_URL`/`VITE_DEV_API_PROXY`, ou CORS non autorisé (voir la console du navigateur). |
| `DJANGO_SECRET_KEY est obligatoire` | `DEBUG=false` sans clé : renseigner `DJANGO_SECRET_KEY`. |
| Connexion PostgreSQL refusée | `docker compose up -d postgres` ; port **5433** hors Docker. |
| `npm.ps1 cannot be loaded` (Windows) | Utiliser `npm.cmd`. |
