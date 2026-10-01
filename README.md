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

## Consumer Kafka GRIDD

Le consumer Kafka est desactive par defaut. Lorsqu'il est active, il utilise
TLS avec validation du certificat CA et SASL SCRAM-SHA-256. Le certificat est
lu depuis `KAFKA_CA_CERT_PATH`; les identifiants restent uniquement dans le
fichier `.env` local.

Les messages Kafka valides sont transformes en `ObservationInput`, puis passent
par le meme `ObservationProcessor` que le simulateur. Un timestamp explicite
(`timestamp`, `observed_at` ou `observedAt`) devient `observedAt`. En son absence,
`observedAt` reste nul et la date `receivedAt` est attribuee par PostgreSQL lors
de la persistance.

KafkaJS confirme automatiquement l'offset apres le retour normal du handler.
Un message JSON ou metier invalide est journalise puis ignore, ce qui permet au
consumer de poursuivre. Une erreur du pipeline est relancee et n'est donc pas
confirmee silencieusement. Cette distinction fournit le point d'extension pour
une future DLQ sans en creer une dans cette phase.

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
