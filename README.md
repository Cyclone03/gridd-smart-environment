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
