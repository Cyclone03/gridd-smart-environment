# Module IA

Prédiction climatique **H+1** (température et humidité intérieures) pour chacune
des six zones GRIDD, avec un modèle Keras par zone, et instantané météo
Open-Meteo partagé. Les résultats sont publiés sur le bus d'événements ; le
module Database les persiste et le module Realtime les pousse aux navigateurs.

Le module fait partie de l'API (`apps/api/modules/ia`) mais tourne dans sa
propre image Docker (cible `ia`, avec TensorFlow) : l'image de l'API reste
légère et n'importe jamais TensorFlow ni numpy.

## Contrat

| | |
|---|---|
| Commandes | `python manage.py run_ai_predictions` (planificateur : un cycle immédiat puis toutes les `AI_PREDICTION_INTERVAL_SECONDS`) ; `--once [--zone <code>]` (un cycle) ; `python manage.py ai_prediction_healthcheck` |
| Kafka sortie | `KAFKA_TOPIC_AI_PREDICTIONS` (`gridd.backend.ai_prediction.events`) : `climate_prediction.generated` (clé : zone), `weather_snapshot.generated` (clé : `weather`), source `ai_prediction_service` — voir `docs/events.md` |
| Kafka entrée | aucune |
| Données lues | dernières mesures `temperature` et `humidity` des zones actives (base, ou API REST avec `AI_OBSERVATION_SOURCE=api`) ; Open-Meteo |
| État local | registre SQLite des publications et battement de cœur dans `AI_STATE_DIR` (volume persistant) |

### Réglages

| Variable | Défaut | Rôle |
|---|---|---|
| `AI_APPROVED_SCALER_SHA256` | vide | les 12 empreintes `scaler_x`/`scaler_y` approuvées (voir Dépannage) ; vide = aucun modèle chargé, météo seule |
| `AI_ISOLATED_ENVIRONMENT` | `false` (`true` dans l'image `ia`) | confirmation que les artefacts sont chargés dans un conteneur isolé |
| `AI_ARTIFACT_MANIFEST_PATH` | `modules/ia/artifacts/manifest.json` | manifeste des artefacts |
| `AI_STATE_DIR` | `~/.gridd-ai-prediction` (`/var/lib/ai-predictions` dans l'image) | dossier du registre et du battement de cœur |
| `AI_PREDICTION_LEDGER_PATH`, `AI_PREDICTION_HEARTBEAT_PATH` | dans `AI_STATE_DIR` | chemins explicites |
| `AI_PREDICTION_INTERVAL_SECONDS` | `3600` | intervalle entre deux cycles |
| `AI_PREDICTION_ALIGN_SECONDS` / `AI_PREDICTION_ALIGN_OFFSET_SECONDS` | `900` / `60` | cycles lancés à HH:01, HH:16, HH:31 ou HH:46 (créneaux Open-Meteo, voir Dépannage) ; `0` désactive l'alignement |
| `AI_PREDICTION_HEARTBEAT_INTERVAL_SECONDS` / `_MAX_AGE_SECONDS` | `30` / `180` | battement de cœur et seuil du healthcheck |
| `AI_OBSERVATION_SOURCE` | `database` | `database` (lecture directe) ou `api` (`GRIDD_API_BASE_URL`) |
| `OPEN_METEO_LATITUDE`, `OPEN_METEO_LONGITUDE` | — (obligatoires) | position pour Open-Meteo |
| `AI_HTTP_TIMEOUT_SECONDS` | `10` (ou `HTTP_TIMEOUT_SECONDS`) | délai des appels HTTP |
| `EVENT_BUS`, `KAFKA_*` | ceux de l'API | bus interne du backend (pas `KAFKA_SENSORS_*`) |

## Structure

```text
core/                              Python pur : bibliothèque standard, numpy à l'inférence
  domain/        observations, météo, événements (ClimatePredictionEvent,
                 WeatherSnapshotEvent → enveloppe shared.kernel.events.Event),
                 résultats, registre (PredictionClaim), SchedulerSettings, zones
  inference/     contrat X/Y, manifeste et registre d'artefacts, approbation des
                 scalers, ArtifactLoader (vérifications SHA-256), ModelPredictor
  errors/        une exception par fichier
  ports/         ObservationSource, WeatherSource, PredictionPublisher,
                 PredictionLedger, Heartbeat
  services/      DataCollectionService, PredictionOrchestrator, PredictionCycle,
                 PredictionScheduler
adapters/
  persistence/   DatabaseObservationSource (ORM), SQLitePredictionLedger, FileHeartbeat
  http/          OpenMeteoWeatherSource, GriddApiObservationSource, http_json
  messaging/     EventBusPredictionPublisher (bus partagé shared.messaging)
  inference/     keras_artifact_loaders (TensorFlow / joblib, imports tardifs)
artifacts/       manifest.json + zone1…zone6 (modèle .h5, scalers .joblib)
composition.py   assemble le cœur et les adaptateurs selon les réglages AI_*
management/      run_ai_predictions, ai_prediction_healthcheck
```

Dépendances d'inférence : `requirements-ia.txt` (installé seulement dans
l'image `ia`).

## Fonctionnement

1. `PredictionCycle` charge les six modèles. Avant toute désérialisation,
   `ArtifactLoader` exige `AI_ISOLATED_ENVIRONMENT=true`, l'approbation des deux
   empreintes de scaler de la zone et vérifie le SHA-256 de chaque fichier.
   Une zone en échec n'empêche pas les autres ; sans aucun modèle, seule la
   météo est publiée et le cycle se termine en erreur.
2. La météo (conditions courantes + prévision H+1) est collectée une fois et
   publiée (`weather_snapshot.generated`).
3. Pour chaque zone, dans l'ordre du mapping confirmé :
   - les entrées doivent avoir `quality_status=normal`, des unités °C/C et %,
     des horodatages capteur explicites, moins de 10 minutes, et au plus
     5 minutes d'écart entre mesures intérieures et Open-Meteo ;
   - les caractéristiques sont produites dans l'ordre X confirmé
     `[indoor_temperature, indoor_humidity, outdoor_temperature, outdoor_humidity]`
     (conditions météo courantes, jamais la prévision) ; la sortie est
     `[indoor_temperature, indoor_humidity]` ;
   - `target_at` = horodatage le plus récent des quatre entrées + 1 h ;
     toutes les publications sont marquées `experimental` (horizon H+1 de
     l'entraînement non confirmé) ;
   - la version publiée contient le numéro du modèle et le SHA-256 du H5.
4. Chaque échec est journalisé et isolé à sa zone.

Mapping confirmé (`core/domain/zones.py`) :

| Modèle | Code de zone |
|---|---|
| `modelZone1` | `open-workspace` |
| `modelZone2` | `server-equipment-room` |
| `modelZone3` | `professors-office` |
| `modelZone4` | `individual-work-cubicle-01` |
| `modelZone5` | `meeting-room` |
| `modelZone6` | `individual-work-cubicle-02` |

Restent à confirmer auprès de l'auteur des modèles : le reshape
`(batch, 4, 1)` utilisé à l'entraînement, l'horizon exact H+1 des cibles et les
versions d'entraînement (TensorFlow, Python, NumPy, joblib).

### Déduplication et reprise

`SQLitePredictionLedger` utilise la zone et l'instant d'entrée UTC comme clé et
en dérive un UUID stable. Une entrée déjà publiée est ignorée ; après une erreur
ou un redémarrage, une prédiction en attente est republiée avec le même UUID et
le même contenu, que le module Database déduplique par `event_id`. **Le dossier
d'état doit être un volume persistant** (`ai-prediction-state` dans le
docker-compose), sinon une prédiction peut être recalculée et republiée.

La publication attend l'accusé du broker (`acks=all`, idempotence) via
`shared.messaging` ; le planificateur ne lance jamais deux cycles en parallèle,
exécute chaque cycle dans un processus neuf (mémoire de TensorFlow rendue) et
continue après un cycle en erreur. Le battement de cœur indique que le
planificateur est vivant, pas que le dernier cycle a réussi.

## Exécution

Docker (depuis la racine du dépôt) : service `ai-prediction` de
`apps/api/docker-compose.yml`, image construite avec `target: ia`, même
`apps/api/.env` que l'API.

Hors Docker :

```bash
cd apps/api
pip install -r requirements-ia.txt
export AI_STATE_DIR=./state AI_ISOLATED_ENVIRONMENT=true
python manage.py run_ai_predictions --once          # un cycle
python manage.py run_ai_predictions                 # planificateur
```

Avec `EVENT_BUS=memory`, le processus persiste lui-même les événements (bus
synchrone) : pratique pour un essai local sans Kafka.

Tests : `python manage.py test modules.ia` (les tests de `ModelPredictor`
sont ignorés si numpy n'est pas installé).

## Réutiliser le module

Le cœur ne connaît ni Django, ni Kafka, ni TensorFlow : il reçoit ses
dépendances par les cinq ports et deux fonctions de chargement
(`model_loader`, `scaler_loader`). Pour l'intégrer ailleurs, copier `core/`,
`artifacts/` et `shared/kernel/`, puis fournir une source d'observations, une
source météo (l'adaptateur Open-Meteo n'utilise que la bibliothèque standard),
un publieur et, si besoin, `SQLitePredictionLedger` et `FileHeartbeat`.

## Dépannage

### `ArtifactTrustError: Both scaler SHA-256 values require explicit provenance approval`

Comportement voulu : les scalers `.joblib` sont des pickles, dont la lecture
peut exécuter du code. Ils ne sont chargés que si leurs empreintes figurent
dans `AI_APPROVED_SCALER_SHA256`. Le message indique la zone, les empreintes
non approuvées et le nombre d'empreintes reçues : `0 approved digest(s)
configured` signifie que la variable est vide ou absente du conteneur.

Approuver est une décision de confiance, à prendre après revue :

1. vérifier que chaque fichier correspond au manifeste (SHA-256) et au blob Git
   enregistré (`git hash-object <fichier>` = `git_blob`) ;
2. confirmer auprès de l'auteur des modèles que le commit source
   (`source.commit` du manifeste) est bien celui de l'entraînement ;
3. renseigner les 12 empreintes `scaler_x`/`scaler_y`, par exemple :

```bash
python -c "import json;m=json.load(open('modules/ia/artifacts/manifest.json'));print(','.join(z['files'][k]['sha256'] for z in m['zones'].values() for k in ('scaler_x','scaler_y')))"
```

Séparateurs acceptés : virgule, point-virgule, espace ou retour à la ligne ;
majuscules (sortie de `Get-FileHash`) et guillemets tolérés. Une valeur qui
n'est pas une empreinte SHA-256 fait échouer le démarrage. Les modèles `.h5`
sont vérifiés par leur SHA-256 à chaque chargement.

### `Indoor and outdoor timestamps differ by more than five minutes`

Open-Meteo donne ses conditions courantes par pas de 15 minutes
(`current.time` = début du quart d'heure, par exemple 16:15 jusqu'à 16:29).
L'orchestrateur exige au plus 5 minutes d'écart avec les mesures intérieures :
un cycle lancé à 16:22 échoue pour toutes les zones. Le planificateur aligne
donc ses cycles sur `AI_PREDICTION_ALIGN_SECONDS` (900) + `AI_PREDICTION_ALIGN_OFFSET_SECONDS`
(60) : le premier cycle attend au plus 15 minutes après le démarrage. Un cycle
manuel (`--once`) n'est pas aligné : le lancer entre HH:01 et HH:04 (ou
HH:16–19, HH:31–34, HH:46–49).

### `temperature observation are stale (… seconds old)`

Aucune mesure récente (moins de 10 minutes) pour la zone : le capteur
n'émet plus, ou ses mesures sont rejetées par l'ingestion (voir les journaux
`[ingestion] message rejeté` du service `kafka-consumer`, par exemple
`zone incohérente` lorsqu'un capteur a changé de zone).

### `Artifact loading requires an isolated environment`

`AI_ISOLATED_ENVIRONMENT` n'est pas `true`. L'image `ia` et le docker-compose
le fixent ; hors Docker, le définir explicitement.

### `Inference dependencies are missing`

Le cycle tourne dans un environnement sans TensorFlow / joblib (image `api`
ou poste local) : utiliser l'image `ia` ou `requirements-ia.txt`.

### Publication impossible / `Disconnected ... in state APIVERSION_QUERY`

Le module publie sur le **bus interne du backend** (`KAFKA_*`, le même que
`kafka-consumer`), jamais sur le cluster des capteurs (`KAFKA_SENSORS_*`). Un
listener `SASL_SSL` exige `KAFKA_SECURITY_PROTOCOL=SASL_SSL`,
`KAFKA_SASL_MECHANISM`, `KAFKA_USERNAME`, `KAFKA_PASSWORD` et
`KAFKA_CA_CERT_PATH` (certificat monté en lecture seule), avec un compte
autorisé à écrire sur `gridd.backend.ai_prediction.events`.
