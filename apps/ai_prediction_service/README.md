# GRIDD AI prediction service

Service Python indépendant. Il collecte les observations, valide leur cohérence
temporelle, exécute le modèle de chaque zone et publie le résultat dans Kafka.
`python -m ai_prediction_service` effectue un cycle ponctuel et
`python -m ai_prediction_service.scheduler` lance le cycle immédiatement puis
selon un intervalle configurable (une heure par défaut).

## Sources de données

- Open-Meteo : coordonnées obligatoires dans `OPEN_METEO_LATITUDE` et
  `OPEN_METEO_LONGITUDE`. Chaque appel récupère les conditions courantes et la
  prévision horaire pour la prochaine heure UTC complète.
- GRIDD : `GRIDD_API_BASE_URL` désigne l'API Django. Le client lit les zones
  actives sur `/api/zones/` puis leurs dernières observations sur
  `/api/observations/latest/`. Les codes sont ceux retournés par l'API, jamais
  déduits des noms `modelZone1` à `modelZone6`.

Le mapping confirmé par Karina est centralisé dans
`src/ai_prediction_service/models/zones.py` :

| Modèle | Code de zone Django |
|---|---|
| `modelZone1` | `open-workspace` |
| `modelZone2` | `server-equipment-room` |
| `modelZone3` | `professors-office` |
| `modelZone4` | `individual-work-cubicle-01` |
| `modelZone5` | `meeting-room` |
| `modelZone6` | `individual-work-cubicle-02` |

## Configuration et utilisation

```text
GRIDD_API_BASE_URL=http://localhost:8000
OPEN_METEO_LATITUDE=45.5088
OPEN_METEO_LONGITUDE=-73.5878
HTTP_TIMEOUT_SECONDS=10
```

`DataCollectionService.collect()` est réutilisé une fois par zone afin qu'une
erreur de collecte n'empêche pas les autres zones d'être traitées. Chaque cycle
fait de vrais appels à Django et Open-Meteo; une indisponibilité, une mesure
manquante ou une donnée périmée entraîne un échec pour la zone concernée. Aucune
donnée synthétique n'est utilisée en remplacement.

## Artefacts des modèles

Les copies de travail sont sous `artifacts/zoneN/`; les H5 historiques non
suivis de `apps/api/` ne sont pas modifiés. `artifacts/manifest.json` consigne
pour chaque copie le chemin source GitLab, l'identifiant Git du blob, le SHA-256
et la taille. Il conserve aussi le SHA-256 de l'ancien H5 local pour faciliter
la comparaison.

L'ordre X confirmé pour les six modèles est
`[indoor_temperature, indoor_humidity, outdoor_temperature, outdoor_humidity]`.
Les deux premières valeurs proviennent des capteurs GRIDD, les deux dernières
d'Open-Meteo. L'ordre Y confirmé est
`[indoor_temperature, indoor_humidity]`. Les formes annoncées restent
`(batch, 4, 1)` vers `(batch, 2)`.

`DataCollectionService.build_model_features()` produit une structure nommée
dans cet ordre. Il exige un point météo explicite afin de ne pas choisir
implicitement entre météo courante et prévision H+1. `ModelPredictor` réordonne
les valeurs par nom selon le contrat confirmé avant l'appel à `scaler_x`.
Après transformation, les valeurs sont converties en tableau NumPy `float32`
puis remodelées en `(batch, 4, 1)`; la sortie
`(batch, 2)` est dénormalisée avec `scaler_y`.

La confirmation du mapping et des ordres X/Y ne confirme pas que le reshape
`(batch, 4, 1)` a réellement été utilisé à l'entraînement, ni que les cibles
correspondent à un horizon exact H+1. Les versions d'entraînement TensorFlow,
Python, NumPy et joblib restent également à confirmer.

Le registre vérifie que le mapping et les ordres consignés dans le manifeste
correspondent au contrat centralisé. Avant toute désérialisation `.joblib`,
`ArtifactLoader` exige un environnement isolé et l'approbation explicite des
empreintes SHA-256 de chaque scaler. La provenance du manifeste reste à
confirmer indépendamment.

Les dépendances d'inférence sont déclarées dans l'extra `inference`
(`tensorflow==2.21.0`, `keras==3.15.1`, `scikit-learn==1.9.1`).

## Orchestration et temporalité

`PredictionOrchestrator.run_zone()` traite une zone et `run_all()` traite les
six codes dans l'ordre du mapping confirmé, en isolant et journalisant chaque
échec. Les entrées doivent avoir `quality_status=normal`, des unités °C/C et
%, des horodatages capteur explicites, moins de 10 minutes et un écart maximal
de 5 minutes entre les observations intérieures et Open-Meteo. Les données
Open-Meteo courantes sont utilisées; la prévision météo future n'est pas
injectée dans les caractéristiques.

`target_at` est ancré au plus récent des horodatages des quatre valeurs
cohérentes, puis augmenté d'une heure. Le modèle d'entraînement n'ayant pas de
contrat H+1 confirmé, toutes les publications sont obligatoirement marquées
`experimental`; aucune prédiction opérationnelle n'est émise.

La version du modèle publiée contient le numéro de modèle et le SHA-256 H5.
La commande exige les variables suivantes, sans charger de fichier `.env` :

```text
AI_ARTIFACT_MANIFEST_PATH=artifacts/manifest.json
AI_APPROVED_SCALER_SHA256=<les 12 empreintes scaler approuvées, séparées par des virgules>
AI_ISOLATED_ENVIRONMENT=true
GRIDD_API_BASE_URL=http://localhost:8000
OPEN_METEO_LATITUDE=45.5088
OPEN_METEO_LONGITUDE=-73.5878
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
AI_PREDICTION_LEDGER_PATH=./state/predictions.sqlite3
```

Après approbation des artefacts et installation dans l'environnement isolé :

```powershell
python -m pip install ".[inference]"
python -m ai_prediction_service
```

Pour exécuter automatiquement un cycle dès le démarrage puis toutes les heures :

```powershell
$env:AI_PREDICTION_INTERVAL_SECONDS = "3600"
$env:AI_PREDICTION_LEDGER_PATH = (Join-Path (Get-Location) "state\predictions.sqlite3")
python -m ai_prediction_service.scheduler
```

Le scheduler ne lance jamais deux cycles en parallèle. Il continue après un
cycle en erreur et retente à l'intervalle suivant. Un heartbeat indépendant du
résultat métier alimente le healthcheck; il vérifie que le processus périodique
est vivant, pas que les API ou Kafka ont réussi le dernier cycle.

Les clients HTTP utilisent uniquement la bibliothèque standard Python. Pour lancer
les tests depuis la racine du dépôt sous PowerShell :

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "apps\ai_prediction_service\src")
.\.venv\Scripts\python.exe -m unittest discover -s apps\ai_prediction_service\tests -v
```

## Publication Kafka des prédictions

`KafkaPredictionProducer` publie l'événement `climate_prediction.generated`
sur `gridd.backend.ai_prediction.events` par défaut. Il reprend l'enveloppe
JSON interne du backend et utilise le code de zone comme clé Kafka.
`KAFKA_BOOTSTRAP_SERVERS` est obligatoire; le topic peut être remplacé avec
`KAFKA_TOPIC_AI_PREDICTIONS`. La connexion accepte les variables existantes
`KAFKA_SECURITY_PROTOCOL`, `KAFKA_SASL_MECHANISM`, `KAFKA_USERNAME`,
`KAFKA_PASSWORD`, `KAFKA_CA_CERT_PATH` et `KAFKA_PUBLISH_TIMEOUT_SECONDS`.

Le producteur attend l'accusé de livraison (`acks=all`, idempotence activée)
et retourne le topic, la partition et l'offset confirmés. Le service consomme
maintenant ce reçu et journalise l'identifiant de zone, la cible, la version du
modèle et l'accusé Kafka. Pour une première démonstration, utiliser uniquement
un broker local isolé; ne pas pointer `KAFKA_BOOTSTRAP_SERVERS` vers un broker
partagé. Voir [le contrat Kafka](../../docs/events.md).

## Déduplication et reprise

`SQLitePredictionLedger` conserve l'état dans `AI_PREDICTION_LEDGER_PATH` et
utilise la zone et l'instant d'entrée UTC comme clé. Un UUID stable est dérivé
de cette clé. Les exécutions déjà confirmées sont ignorées; après une erreur
ou un redémarrage, un événement en attente est rejoué avec le même UUID et le
même contenu. Monte ce fichier sur un volume persistant : sans ce volume, l'état
de déduplication local est perdu.

Kafka et le ledger local ne partagent pas de transaction distribuée. Si le
broker accepte un message mais que son accusé ou la mise à jour locale est
perdu, le même événement peut être envoyé à nouveau. Son UUID et son contenu
restent identiques, ce qui permet au consommateur Database existant de
l'la déduplication par `event_id`; cela ne prétend pas garantir une livraison Kafka
exactement une fois.

## Docker

`Dockerfile` construit un worker non privilégié avec les artefacts vérifiés.
`docker-compose.yml` ne crée ni Django, ni Kafka, ni PostgreSQL : il raccorde le
worker à un réseau Docker **existant** et monte un volume dédié au ledger et au
heartbeat. Configure les variables requises dans l'environnement du processus
Compose ou dans un gestionnaire de secrets; aucun fichier `.env` n'est créé ou
modifié par le service.

Variables requises pour Compose :

- `AI_DOCKER_NETWORK` : réseau existant commun à Django et Kafka.
- `GRIDD_API_BASE_URL`, `OPEN_METEO_LATITUDE`, `OPEN_METEO_LONGITUDE`.
- `KAFKA_BOOTSTRAP_SERVERS` et les paramètres d'authentification nécessaires.
- `AI_APPROVED_SCALER_SHA256` : les 12 empreintes approuvées.
- `AI_ISOLATED_ENVIRONMENT=true` : confirmation explicite requise par le
  chargeur des artefacts.

`AI_PREDICTION_INTERVAL_SECONDS` vaut `3600` par défaut. Pour utiliser TLS,
`KAFKA_CA_CERT_PATH` doit désigner un certificat monté en lecture seule dans le
conteneur. L'image vérifie la fraîcheur du heartbeat avec
`python -m ai_prediction_service.healthcheck`.

Exemple PowerShell (les valeurs d'accès restent à fournir par l'opérateur) :

```powershell
$env:AI_DOCKER_NETWORK = "<réseau Docker existant>"
$env:AI_ISOLATED_ENVIRONMENT = "true"
# Définir les autres variables requises depuis la configuration sécurisée.
docker compose -f apps/ai_prediction_service/docker-compose.yml up --build -d
```
