# Déploiement Docker

Le frontend et l'API ont chacun leur `Dockerfile` et leur `docker-compose.yml`.
Ils se construisent, se déploient et se mettent à jour indépendamment.

## Frontend (`apps/web/`)

```bash
cd apps/web
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
docker compose config --quiet
docker compose build api
docker compose up -d api
# À lancer uniquement après vérification du broker et du groupe configurés :
docker compose up -d kafka-consumer
docker compose logs -f api kafka-consumer
# Module IA (image « ia », TensorFlow) :
docker compose build ai-prediction
docker compose up -d ai-prediction
docker compose logs -f ai-prediction
```

Le fichier `apps/api/docker-compose.yml` déclare `api`, `kafka-consumer` et
`ai-prediction`. Il ne démarre pas PostgreSQL, Redis ou Kafka ; ces services
doivent déjà être accessibles depuis les conteneurs et configurés dans `.env`.
`docker compose up -d` démarre aussi le consommateur. Celui-ci utilise les
groupes configurés et valide les offsets après traitement : vérifier
`EVENT_BUS=kafka`, le broker et les groupes avant de le démarrer sur un
environnement partagé, avec l'autorisation nécessaire.

| Service | Rôle | Notes |
|---|---|---|
| `api` | Daphne (ASGI) : REST, WebSocket, admin | santé `GET /api/health/`; monte le certificat capteur; pas de migrations automatiques |
| `kafka-consumer` | `manage.py run_consumers` | modules `ingestion`, `database`, `alarms`, `realtime`; monte le certificat capteur depuis `apps/api/secrets/` |
| `ai-prediction` | `manage.py run_ai_predictions` (image `ia`) | module `ia` : lit la base, appelle Open-Meteo, publie sur le bus interne (`EVENT_BUS=kafka` forcé) ; persisté par `kafka-consumer` ; volume `ai-prediction-state` **obligatoire** ; santé `manage.py ai_prediction_healthcheck` |
| PostgreSQL, Redis, Kafka | Dépendances externes | aucun de ces services n'est défini dans ce Compose |

Les deux images sont construites depuis `apps/api` avec `docker/Dockerfile` :
`--target api` (défaut, dernière étape) et `--target ia` (même code +
`requirements-ia.txt`). Le service `ai-prediction` utilise le même
`apps/api/.env` que l'API : y ajouter les variables `AI_*` et
`OPEN_METEO_*` (voir `.env.example` et `apps/api/modules/ia/README.md`). Les
réglages propres à l'image (`AI_ISOLATED_ENVIRONMENT`, `AI_STATE_DIR`, chemins
du registre et du manifeste) sont fixés dans `environment:` et ne peuvent pas
être écrasés par le fichier `.env`.

### Mise à jour « un capteur par zone » (migration 0018)

1. Sauvegarder la base (`pg_dump`).
2. Déployer, puis appliquer les migrations dans le conteneur `api` :
   `python manage.py migrate`. Les capteurs `environmental-nodeXX` deviennent
   `<zone>-<mesure>` ; aucune observation n'est supprimée.
3. Redémarrer `kafka-consumer` (caches de capteurs).
4. Récupérer les mesures rejetées d'une période, dans `kafka-consumer` :
   `python manage.py replay_sensor_topics --since <ISO 8601> --dry-run`, puis
   sans `--dry-run`. Le rejeu est idempotent et peut être relancé.

L'image API :

- installe les dépendances dans un environnement virtuel, étape séparée ;
- collecte les fichiers statiques de l'admin à la construction (servis par
  WhiteNoise), avec une clé factice : **aucun secret n'est intégré** ;
- s'exécute sous l'utilisateur `gridd` (uid 10001) ;
- n'exécute pas de migration automatiquement : appliquer les migrations
  explicitement après vérification de la base ciblée.

### Configuration des services externes

Renseigner les variables standard de `.env` (`DB_HOST`, `REDIS_URL`,
`KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_SENSORS_*`) avec des adresses joignables
depuis les conteneurs. Une adresse `localhost` désigne le conteneur lui-même,
pas l'hôte Windows ni un service distant.

### Kafka

- Les capteurs réels se lisent sur le Kafka GRIDD (`KAFKA_SENSORS_*`, certificat
  dans `apps/api/secrets/`) ; les événements internes passent par un Kafka
  géré (`KAFKA_*`).
- `kafka-consumer` crée les topics internes au démarrage si
  `KAFKA_AUTO_CREATE_TOPICS` est activé.
  En production, prévoir au moins 3 partitions et un facteur de réplication
  adapté au cluster.
- Montée en charge : dédier un service par module avec
  `run_consumers --module <module>`. `database` et `realtime` peuvent être
  dupliqués (Kafka répartit les partitions entre les instances d'un module).
  `ingestion` et `alarms` gardent une vue locale de leur état (historique
  récent des capteurs, état des règles) : les laisser à **une instance** chacun,
  ce qui suffit largement pour quelques centaines de capteurs.
- Les données Kafka sont en transit ; la donnée de référence est dans
  PostgreSQL.
- **Un préfixe de consumer group par déploiement.** Les instances d'un même
  module se partagent les partitions de leur groupe
  (`<KAFKA_CONSUMER_GROUP_PREFIX>.<module>`). C'est voulu pour dupliquer
  `database` *sur la même base* ; mais une autre instance du backend
  connectée au même Kafka avec le même préfixe (poste de développement,
  ancienne version, second `docker compose`, autre base) reçoit une partie des
  partitions **et donc une partie des zones**, sans aucune erreur. Donner un
  préfixe distinct à chaque déploiement (`gridd-prod`, `gridd-dev-<nom>`…).

### Débit et retard des consommateurs

Symptôme : les écrans affichent des mesures de plus en plus anciennes ;
`/api/health/` indique `"status": "degraded"` et `data.age_seconds` grandit ;
`kafka_groups` montre un `retard` qui augmente.

Ce qui détermine le débit :

- **Traitement par lot** (`KAFKA_BATCH_SIZE`, 500) : les publications d'un
  lot partent sans attente, leurs accusés sont attendus une fois, puis les
  offsets sont validés en un appel. Avant, chaque message attendait deux
  allers-retours avec le broker : quelques messages par seconde avec un
  Kafka distant, moins que le débit des capteurs, d'où un retard croissant.
- **Moteur d'alarmes** : une règle toujours déclenchée (ex. « température >
  10 °C ») republiait l'alerte et l'état à chaque mesure. Désormais un état
  inchangé et une alerte « en cours » ne sont republiés qu'une fois par
  minute ; déclenchements et retours à la normale restent immédiats.
- **Surveillance** : le service `kafka-consumer` a un healthcheck
  (battement de cœur) ; un module bloqué plus de
  `KAFKA_CONSUMER_STALL_SECONDS` arrête le processus, que Docker redémarre.

Après un arrêt prolongé, l'arriéré est absorbé par lots en quelques minutes.

### Données d’une partie des espaces absentes

Symptôme : certains espaces n'ont plus aucune mesure récente (badge « Pas de
données récentes ») alors que d'autres continuent, et les capteurs émettent
toujours.

Les observations validées sont publiées sur
`gridd.backend.ingestion.observations` avec le **code de zone comme clé** :
toutes les mesures d'une zone passent par la même partition
(`crc32(code) % nombre de partitions`). Si une partition n'est plus lue par
cette instance, toutes ses zones disparaissent ensemble.

1. Identifier qui lit chaque partition et le retard :

   ```bash
   docker compose exec kafka-consumer python manage.py kafka_groups
   ```

   Plusieurs membres dans `gridd-backend.database`, ou une partition
   « lu par » une autre machine (ou `rdkafka` : instance sans identifiant,
   donc antérieure à cette version) → une autre instance partage le groupe.
   Au démarrage, chaque module journalise aussi ses partitions
   (`partitions attribuées : …`) et avertit si certaines sont lues ailleurs.

2. Arrêter l'autre instance, ou lui donner un autre
   `KAFKA_CONSUMER_GROUP_PREFIX`.

3. Récupérer les mesures manquantes, tant que Kafka les conserve (rétention
   par défaut : 7 jours). Tous les consommateurs du groupe arrêtés :

   ```bash
   kafka-consumer-groups.sh --bootstrap-server <broker> \
     --group gridd-backend.database \
     --topic gridd.backend.ingestion.observations \
     --reset-offsets --to-datetime 2026-11-06T08:00:00.000Z --execute
   ```

   puis redémarrer `kafka-consumer`. L'enregistrement est idempotent
   (`event_id` = topic + partition + offset) : les messages déjà en base sont
   ignorés. Les modules en aval reçoivent les mesures rejouées (alarmes
   évaluées sur des valeurs anciennes, mises à jour temps réel).

   Si la rétention du topic interne est dépassée, rejouer depuis les topics
   capteurs du Kafka GRIDD : même commande sur le groupe
   `gridd-backend.ingestion` et ses topics, puis
   `run_consumers --module ingestion --replay-backlog`.

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
- **Accès** : l'API n'a pas d'authentification pour le moment ; ne l'exposer
  que sur un réseau de confiance ou derrière un proxy qui contrôle l'accès.
- **Secrets** : uniquement dans `.env` (non versionné) ou le gestionnaire de
  secrets de l'orchestrateur.
- **Journaux** : les deux applications écrivent sur la sortie standard
  (`docker compose logs`). `LOG_LEVEL` côté API, `LOG_REQUESTS=true` côté
  frontend pour tracer chaque requête.
- **Diagnostic** : `GET /healthz` (frontend), `GET /api/health/` (API : base de
  données, couche temps réel, bus d'événements). `run_consumers --list` affiche
  les abonnements de chaque module ; `kafka_groups` affiche les membres, les
  partitions et le retard de chaque consumer group. `docker compose ps` affiche l'état de
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

### Refonte modulaire (bus Kafka)

L'environnement de refonte n'avait ni démon Docker ni accès aux images Kafka :
aucun broker réel n'a pu être démarré. Ont été vérifiés : `docker compose config`
(tous les profils), la suite de tests complète avec le bus mémoire (même code
de modules qu'avec Kafka), le consommateur Kafka et la requête-réponse avec des
clients confluent-kafka simulés, et l'arrêt propre de `run_consumers` quand le
broker est injoignable. Premier démarrage à surveiller : `docker compose logs -f workers`
(création des topics, abonnement de chaque module).
