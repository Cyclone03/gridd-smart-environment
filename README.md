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

## Démarrage complet (Docker local)

Depuis la racine du dépôt, une seule commande construit et démarre la pile
locale isolée :

```bash
docker compose up --build -d
```

Elle démarre PostgreSQL local (volume dédié), Redis, Kafka KRaft, l'API Django
(migrations et zones de base), les consommateurs Kafka, le worker IA et le
dashboard React. Les événements internes restent sur le Kafka local. Le
conteneur `consumers` lit les paramètres du broker des capteurs dans le vrai
fichier [`apps/api/.env`](apps/api/.env) et monte son certificat depuis
`apps/api/secret/gridd-kafka-ca.crt`; ces fichiers ne sont ni copiés dans les
images ni modifiés.

- Dashboard : <http://localhost:3000>
- API et WebSocket : <http://localhost:8001> et `ws://localhost:8001`
- Kafka local pour les producteurs sur l'hôte : `localhost:19092`

Arrêter sans supprimer les données persistées :

```bash
docker compose down
```

Les volumes nommés sont conservés. Ne faire `docker compose down -v` que si
la suppression explicite de la base locale, du ledger IA et des données Kafka
est souhaitée.

**Aucune mesure simulée n'est créée.** Le compose initialise les six zones et
leurs capteurs, mais le worker attend des observations réelles arrivant sur
le broker capteurs configuré dans `apps/api/.env`. Les observations reçues
seront traitées par les modules et persistées dans PostgreSQL local; les
événements internes ne sont pas publiés sur le broker capteurs. Sans nouvelles
mesures réelles, il ne publiera pas de prédiction. Les prédictions restent
expérimentales. De plus, le
chargement des scalers `.joblib` est volontairement non autorisé dans cette
configuration tant que leurs empreintes exactes n'ont pas reçu une approbation
explicite.

Suivi de démarrage et diagnostic :

```bash
docker compose ps
docker compose logs -f api consumers ai-prediction web
```

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
