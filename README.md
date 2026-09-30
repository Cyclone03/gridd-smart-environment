# GRIDD Smart Environment Dashboard

Monorepo du tableau de bord GRIDD Smart Environment.

## Prerequis

- Node.js 20 ou plus recent
- pnpm 10

## Backend

Copier `.env.example` vers `.env`, puis demarrer l'API :

```bash
pnpm install
pnpm dev:api
```

L'endpoint de verification est disponible sur `GET http://localhost:3000/api/health`.
