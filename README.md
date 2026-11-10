# GRIDD — Surveillance environnementale intérieure

GRIDD collecte, surveille et analyse les conditions d'un espace intérieur
(température, humidité, occupation et niveau sonore) à partir des capteurs
publiés sur Kafka. Des règles d'alarme configurables sont évaluées à chaque
mesure.

Les mesures se consultent aussi en temps réel et sur une période choisie
(historique, corrélations). Pas d'authentification pour le moment.

Le dépôt contient **deux applications indépendantes**, chacune avec ses
dépendances, sa configuration, son Dockerfile et son cycle de déploiement :

| Application | Dossier | Technologies | Rôle |
|---|---|---|---|
| Frontend | [`apps/web/`](apps/web/README.md) | React 19, TypeScript, Vite, React Router, Recharts, serveur Node.js | Interface de consultation et de configuration |
| API | [`apps/api/`](apps/api/README.md) | Django 5/6, Django REST Framework, Channels, PostgreSQL, Redis, Kafka | Modules autonomes reliés par Kafka : ingestion, persistance, alarmes, temps réel, API REST et WebSocket |

Elles communiquent **uniquement** par l'API documentée dans
[`docs/api.md`](docs/api.md) : REST sous `/api/`, temps réel sur `/ws/dashboard/`.

```text
Capteurs ──► Kafka ◄──► modules du backend (ingestion · database · alarms · realtime)
                              │ database : seul à écrire dans PostgreSQL
                              ▼
                  Routage REST /api/ + WS /ws/ ◄──── Frontend (Node.js, navigateur)
```

Architecture détaillée : [`docs/architecture.md`](docs/architecture.md).

## Structure

```text
gridd/
├── apps/
│   ├── web/             # Frontend (voir apps/web/README.md)
│   │   ├── src/         # components, views, layouts, routes, services,
│   │   │                # requests, resources, composables, stores, …
│   │   ├── server/      # serveur HTTP Node.js de production
│   │   ├── tests/       # Vitest + Testing Library
│   │   └── Dockerfile · docker-compose.yml · .env.example
│   └── api/             # API Django (voir apps/api/README.md)
│       ├── config/      # paramètres, routage HTTP et WebSocket
│       ├── shared/      # noyau commun : messagerie Kafka, contrats, HTTP
│       ├── modules/     # database, ingestion, alarms, observations,
│       │                # history, realtime, health, simulator
│       ├── tests/       # règles d'architecture, routage
│       ├── docker/      # point d'entrée du conteneur
│       └── Dockerfile · docker-compose.yml · .env.example
├── docs/                # documentation technique
└── .github/workflows/   # intégration continue
```

## Démarrage rapide (Docker)

```bash
# 1. API + modules (workers) + Kafka + PostgreSQL + Redis
cd apps/api
cp .env.example .env            # renseigner au minimum DJANGO_SECRET_KEY et DB_PASSWORD
docker compose up -d --build
docker compose exec api python manage.py seed_gridd        # données de démonstration
docker compose exec api python manage.py createsuperuser

# 2. Frontend (indépendant de l'API)
cd ../web
cp .env.example .env            # GRIDD_API_URL=http://localhost:8000
docker compose up -d --build
```

Ouvrir <http://localhost:3000>. L'admin Django est sur <http://localhost:8000/admin/>.

Pour un environnement de développement sans Docker, voir
[`docs/installation.md`](docs/installation.md).

## Documentation

| Document | Contenu |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Architecture modulaire, flux, règles, décisions |
| [`docs/events.md`](docs/events.md) | Topics Kafka et contrat des événements |
| [`docs/installation.md`](docs/installation.md) | Installation locale pas à pas |
| [`docs/deployment.md`](docs/deployment.md) | Déploiement Docker et production |
| [`docs/api.md`](docs/api.md) | Contrat de l'API REST et WebSocket |
| [`docs/charts.md`](docs/charts.md) | Graphiques et périodes d'observation |
| [`docs/alarms.md`](docs/alarms.md) | Règles d'alarme : configuration et évaluation |

## Vérifications

```bash
cd apps/api && python manage.py test
cd apps/web && npm run typecheck && npm test
```

## Données sensibles

Ne jamais versionner `.env`, `secrets/`, un certificat ni des identifiants
Kafka : ces chemins sont exclus par `.gitignore` et par les `.dockerignore`.
Tout ce qui est transmis au navigateur (configuration du frontend) est public.
