# GRIDD Smart Environment Dashboard

Monorepo du projet universitaire MGL869. L'application collecte des mesures
environnementales, les conserve dans PostgreSQL, calcule un indice de confort,
cree des alertes et les affiche en temps reel dans un dashboard Vue.

## Prerequis

- Node.js 20 ou une version plus recente
- pnpm 10
- Docker Desktop avec Docker Compose

## Installation initiale

Depuis la racine du depot :

```powershell
pnpm install
Copy-Item .env.example .env
```

Le fichier `.env` contient la configuration locale et les eventuels secrets. Il
est ignore par Git. Ne jamais ajouter de mot de passe ou de certificat reel dans
`.env.example`.

Pour le developpement local avec PostgreSQL fourni par Docker, verifier au
minimum ces valeurs dans `.env` :

```dotenv
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=gridd_dashboard
DATABASE_USER=gridd
DATABASE_PASSWORD=choisir_un_mot_de_passe_local
```

La valeur de `DATABASE_PASSWORD` doit aussi correspondre a celle utilisee par
Docker Compose.

## Choisir le mode d'ingestion

Une seule configuration suffit dans `.env` selon l'utilisation voulue :

| Mode | `SIMULATOR_ENABLED` | `KAFKA_ENABLED` | `KAFKA_PRODUCER_ENABLED` |
| --- | --- | --- | --- |
| Developpement sans GRIDD | `true` | `false` | `false` |
| Lecture des donnees GRIDD | `false` | `true` | `false` |
| Lecture et publication GRIDD | `false` | `true` | `true` |

Le producer Kafka est volontairement desactive par defaut. Ne l'activer que si
la publication sur les topics GRIDD a ete autorisee.

## Demarrage local

Ouvrir trois terminaux a la racine du projet.

Terminal 1 - PostgreSQL et migrations :

```powershell
docker compose up -d postgres
pnpm migration:run
```

Terminal 2 - API NestJS :

```powershell
pnpm dev:api
```

Terminal 3 - dashboard Vue :

```powershell
pnpm dev:web
```

Ouvrir ensuite <http://localhost:5173>. L'API est normalement disponible sur
<http://localhost:3000/api> et son etat sur
<http://localhost:3000/api/health>.

Pour arreter l'application, utiliser `Ctrl+C` dans les terminaux puis :

```powershell
docker compose down
```

## Configuration Kafka GRIDD

Creer le dossier local `secrets` a la racine et y deposer le certificat CA :

```text
secrets/gridd-kafka-ca.crt
```

Le dossier est ignore par Git. Configurer ensuite `.env` avec les vraies
valeurs recues du GRIDD :

```dotenv
KAFKA_ENABLED=true
KAFKA_PRODUCER_ENABLED=false
KAFKA_BROKERS=kafka.gridd-dt.ca:9096
KAFKA_USERNAME=...
KAFKA_PASSWORD=...
KAFKA_CA_CERT_PATH=C:/chemin/absolu/vers/secrets/gridd-kafka-ca.crt
KAFKA_GROUP_ID=gridd-smart-environment-dashboard
```

La connexion utilise TLS avec validation du certificat CA et SASL
SCRAM-SHA-256. Aucun contournement TLS n'est prevu.

Le consumer ecoute :

- `gridd.obs.environmental.temperature`
- `gridd.obs.environmental.humidity`
- `gridd.obs.environmental.co2`
- `gridd.obs.acoustic.sound_level`
- `gridd.obs.occupancy.count`

Les messages valides sont convertis en `ObservationInput` puis empruntent le
meme pipeline que le simulateur. L'unite de temperature GRIDD `C` est
normalisee vers l'unite interne `°C` avant validation.

Lorsque `KAFKA_PRODUCER_ENABLED=true`, le producer publie :

- l'indice de confort dans
  `gridd.derived.environmental.thermal_comfort`;
- `HIGH_CO2` dans `gridd.alert.environmental.high_co2`;
- `HIGH_TEMPERATURE` dans
  `gridd.alert.environmental.high_temperature`;
- `HIGH_SOUND_LEVEL` dans
  `gridd.alert.acoustic.high_sound_level`.

Le producer ne contient aucune logique metier. Il ne publie l'indice qu'apres
le traitement d'une nouvelle observation et ne republie pas une alerte deja
active. Une requete `GET /api/comfort` ne declenche aucune publication.

## Architecture et comportement

```text
Kafka Consumer ----\
                    > ObservationProcessor -> validation -> PostgreSQL
Simulateur --------/                          -> confort et alertes
                                               -> Socket.IO
                                               -> Kafka Producer
```

- Le schema PostgreSQL est gere par migrations TypeORM; `synchronize` reste
  desactive.
- Une observation est conservee avant les publications temps reel et Kafka.
- Une erreur du producer est journalisee sans annuler l'observation deja
  persistee.
- Le consumer utilise une semantique au moins une fois. Une erreur du pipeline
  est propagee afin d'eviter la confirmation silencieuse du message.
- Un message Kafka invalide est journalise et ignore sans bloquer la partition.

## API et temps reel

Endpoints principaux :

- `GET /api/health` : etat de l'API, PostgreSQL et Kafka;
- `GET /api/observations` : toutes les observations;
- `GET /api/observations/latest` : derniere observation de chaque type;
- `GET /api/comfort` : indice de confort courant;
- `GET /api/alerts?status=active|history|all` : alertes filtrees.

Le namespace Socket.IO `/realtime` diffuse :

- `observation.created`
- `comfort.updated`
- `alert.created`
- `alert.resolved`

Les seuils et ponderations du Comfort Index sont configurables par variables
d'environnement. Les alertes hautes utilisent strictement les seuils suivants :
CO2 superieur a 1200 ppm, temperature superieure a 28 °C et niveau sonore
superieur a 70 dBA.

## Verification du projet

```powershell
pnpm build:api
pnpm test:api --runInBand
pnpm --filter @gridd/api test:e2e --runInBand
pnpm build:web
pnpm test:web
```

## Depannage

- Utiliser `http://localhost:5173` plutot que `127.0.0.1` pour respecter la
  configuration CORS locale.
- Si le port API `3000` est occupe, definir par exemple `PORT=3100`,
  `VITE_API_BASE_URL=http://localhost:3100` et
  `VITE_SOCKET_URL=http://localhost:3100`, puis redemarrer l'API et le frontend.
- Si PostgreSQL refuse le role apres un changement de variables, un ancien
  volume Docker peut encore contenir l'ancienne configuration. Ne supprimer ce
  volume que si ses donnees peuvent etre perdues.
- Si Kafka reste `disconnected` ou `error`, verifier le broker, les identifiants,
  le chemin absolu du certificat CA et les droits du consumer group.

## Limites connues

- Il n'y a pas encore de dead-letter queue pour les messages Kafka invalides.
- Il n'y a pas d'outbox transactionnelle : si Kafka devient indisponible apres
  la persistance PostgreSQL, une publication derivee peut etre perdue.
- La semantique au moins une fois du consumer peut produire un doublon apres
  une reprise; le pipeline doit donc rester tolerant aux retraitements.
