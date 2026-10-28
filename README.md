# GRIDD — Confort et bien-être intérieur

GRIDD collecte, surveille et analyse les conditions d'un espace intérieur
(température, humidité, occupation et niveau sonore). Il permet de consulter les
mesures en temps réel ou sur une période choisie, d'en analyser l'évolution et
de définir des règles d'alarme depuis l'interface.

Le dépôt contient **deux applications indépendantes**, chacune avec ses
dépendances, sa configuration, son Dockerfile et son cycle de déploiement :

| Application | Dossier | Technologies | Rôle |
|---|---|---|---|
| Frontend | [`web/`](web/README.md) | React 19, TypeScript, Vite, React Router, Recharts, serveur Node.js | Interface de consultation et de configuration |
| API | [`apps/api/`](apps/api/README.md) | Django 5/6, Django REST Framework, Channels, PostgreSQL, Redis, Kafka | Ingestion, stockage, évaluation des alarmes, API REST et WebSocket |

Elles communiquent **uniquement** par l'API documentée dans
[`docs/api.md`](docs/api.md) : REST sous `/api/`, temps réel sur `/ws/dashboard/`.

```text
Kafka GRIDD ─┐                                      ┌──────────────────────────┐
             ├─► API Django ─► PostgreSQL           │  Frontend (Node.js)      │
Simulateur ──┘     │  ├─ moteur de règles d'alarme  │  sert le build Vite et   │
                   │  └─ Redis (Channels)           │  /env.js (adresse API)   │
                   └── REST /api/ + WS /ws/ ◄───────┤  navigateur → API        │
                                                    └──────────────────────────┘
```

## Structure

```text
gridd/
├── web/                 # Frontend (voir web/README.md)
│   ├── src/             # components, views, layouts, routes, services,
│   │                    # requests, resources, composables, stores, …
│   ├── server/          # serveur HTTP Node.js de production
│   ├── tests/           # Vitest + Testing Library
│   ├── Dockerfile · docker-compose.yml · .env.example
├── apps/
│   └── api/             # API Django (voir apps/api/README.md)
│       ├── config/      # paramètres, ASGI
│       ├── core/        # modèles, API, ingestion, moteur d'alarmes, tests
│       ├── docker/      # point d'entrée du conteneur
│       ├── Dockerfile · docker-compose.yml · .env.example
├── docs/                # documentation technique
└── .github/workflows/   # intégration continue
```

## Démarrage rapide (Docker)

```bash
# 1. API + PostgreSQL + Redis
cd apps/api
cp .env.example .env            # renseigner au minimum DJANGO_SECRET_KEY et DB_PASSWORD
docker compose up -d --build
docker compose exec api python manage.py seed_gridd        # données de démonstration
docker compose exec api python manage.py createsuperuser

# 2. Frontend (indépendant de l'API)
cd ../../web
cp .env.example .env            # GRIDD_API_URL=http://localhost:8000
docker compose up -d --build
```

Ouvrir <http://localhost:3000>. L'admin Django est sur <http://localhost:8000/admin/>.

Pour un environnement de développement sans Docker, voir
[`docs/installation.md`](docs/installation.md).

## Documentation

| Document | Contenu |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Architecture, responsabilités des modules, décisions |
| [`docs/installation.md`](docs/installation.md) | Installation locale pas à pas |
| [`docs/deployment.md`](docs/deployment.md) | Déploiement Docker et production |
| [`docs/api.md`](docs/api.md) | Contrat de l'API REST et WebSocket |
| [`docs/charts.md`](docs/charts.md) | Graphiques et périodes d'observation |
| [`docs/alarms.md`](docs/alarms.md) | Règles d'alarme : configuration et évaluation |

## Vérifications

```bash
cd apps/api && python manage.py test core      # 54 tests backend
cd web && npm run typecheck && npm test        # 51 tests frontend
```

## Données sensibles

Ne jamais versionner `.env`, `secrets/`, un certificat ni des identifiants
Kafka : ces chemins sont exclus par `.gitignore` et par les `.dockerignore`.
Tout ce qui est transmis au navigateur (configuration du frontend) est public.
