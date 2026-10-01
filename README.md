# GRIDD Smart Environment Dashboard

Monorepo du tableau de bord GRIDD Smart Environment.

## Prerequis

- Node.js 20 ou plus recent
- pnpm 10

## Backend

Copier `.env.example` vers `.env`, puis demarrer l'API :

```bash
pnpm install
docker compose up -d postgres
pnpm migration:run
pnpm dev:api
```

Renseigner `DATABASE_PASSWORD` dans le fichier `.env` local avant de demarrer
PostgreSQL. Ce fichier est ignore par Git. Le schema est gere par migrations et
la synchronisation automatique TypeORM est desactivee.

L'endpoint de verification est disponible sur `GET http://localhost:3000/api/health`.

Les observations sont disponibles sur `GET /api/observations` et
`GET /api/observations/latest`.

## Simulateur d'observations

Le simulateur est desactive par defaut. Pour generer localement des observations
de test sans Kafka, definir les variables suivantes dans `.env` :

```dotenv
SIMULATOR_ENABLED=true
SIMULATOR_INTERVAL_MS=5000
```

Les observations simulees passent par le meme `ObservationProcessor` que les
futures sources d'ingestion avant leur persistance dans PostgreSQL.

## Analyse, alertes et temps reel

- `GET /api/comfort` retourne l'indice de confort courant ou une reponse
  `unavailable` lorsque des mesures sont manquantes.
- `GET /api/alerts?status=active|history|all` retourne les alertes selon leur
  etat.
- Le namespace Socket.IO `/realtime` diffuse `observation.created`,
  `alert.created`, `alert.resolved` et `comfort.updated`.

Les seuils et ponderations sont configurables par variables d'environnement.
Ce sont des parametres applicatifs de developpement et non des normes
reglementaires.

## Frontend

Le dashboard Vue est disponible dans `apps/web` :

```bash
pnpm dev:web
pnpm build:web
pnpm test:web
```

Les URLs API et Socket.IO sont centralisees avec `VITE_API_BASE_URL` et
`VITE_SOCKET_URL`. Les graphiques utilisent Chart.js via `vue-chartjs` pour sa
maintenance active, son rendu responsive et son integration Vue legere.
