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
