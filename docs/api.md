# Contrat de l'API

Base : `GRIDD_API_URL` (ex. `https://api.gridd.example.org`). Toutes les
réponses sont en JSON ; les dates suivent ISO 8601 avec décalage horaire,
exprimées dans le fuseau du serveur (`TIME_ZONE`, défaut `America/Toronto`).

## Généralités

### Accès

Pas d'authentification pour le moment : toutes les requêtes, lectures et
écritures, sont acceptées sans jeton. En production, restreindre l'accès à
l'API par le réseau ou un proxy.

### Format des erreurs

```json
{ "detail": "Message lisible", "errors": { "champ": ["message", "…"] } }
```

`errors` n'est présent que pour les erreurs de validation (400).

| Code | Signification |
|---|---|
| 400 | Paramètres ou données invalides (`errors` par champ) |
| 404 | Ressource inconnue |
| 405 | Méthode non disponible (ex. `PUT` sur une règle) |
| 503 | `GET /api/health/` : base de données indisponible ; écriture (règle, plages de confort, paramètres énergétiques) : Kafka ou module Database sans réponse |

### CORS et WebSocket

Les origines listées dans `CORS_ALLOWED_ORIGINS` peuvent appeler l'API depuis
un navigateur. Les WebSocket acceptent ces mêmes origines ainsi que les hôtes de
`ALLOWED_HOSTS` ; toute autre origine reçoit un refus 403.

## Zones, capteurs, observations

### `GET /api/zones/`

Zones actives, triées par nom.

```json
{
  "id": 3,
  "name": "Bureau des professeurs",
  "code": "professors-office",
  "zone_type": "office",
  "description": "",
  "active": true,
  "metrics": ["temperature", "humidity", "sound_level"],
  "threshold_profile": {
    "enabled": false,
    "max_temperature_delta_per_minute": 1.0,
    "max_humidity_delta_per_minute": 5.0,
    "max_co2_delta_per_minute": 800.0,
    "stuck_after_minutes": 15,
    "max_sound_delta_per_minute": null
  }
}
```

`metrics` liste les types de mesure ayant un capteur actif dans la zone
(nouveau). `threshold_profile` ne contient plus que les réglages de qualité
des données : les seuils d'alarme sont des [règles](#règles-dalarme).

### `GET /api/zones/<code>/latest/` — dernière mesure de chaque type pour une zone

### `GET /api/sensors/?zone=<code>` — capteurs actifs

### `GET /api/observations/?zone=<code>&type=<type>` — 1 000 dernières observations

### `GET /api/observations/latest/` — dernière observation de chaque zone et type

Types de mesure : `temperature`, `humidity`, `sound_level`, `occupancy`, `co2`.

## Historique

### `GET /api/zones/<code>/history/`

| Paramètre | Obligatoire | Description |
|---|---|---|
| `type` | non (défaut `temperature`) | Type de mesure |
| `start`, `end` | ensemble | Bornes ISO 8601. Sans fuseau, interprétées dans `TIME_ZONE`. `end` > `start`, `start` ≤ maintenant, durée ≤ `HISTORY_MAX_RANGE_DAYS` (31 j). |
| `bucket_minutes` | non | Granularité parmi 1, 5, 15, 30, 60, 180, 360, 720, 1440 ; au plus `HISTORY_MAX_POINTS` (3 000) créneaux. Absente : la plus fine produisant au plus `HISTORY_TARGET_POINTS` (400) créneaux. |
| `hours` | compatibilité | 1, 6, 24 ou 168 (granularité 5, 5, 15, 60 min) |
| `date` | compatibilité | `AAAA-MM-JJ` : journée locale complète, créneaux de 15 min |

Priorité : `start`/`end`, puis `date`, puis `hours` (défaut 24).

Exemple : `GET /api/zones/meeting-room/history/?type=temperature&start=2026-10-27T08:00:00-04:00&end=2026-10-27T12:00:00-04:00`

```json
{
  "zone_code": "meeting-room",
  "type": "temperature",
  "start": "2026-10-27T08:00:00-04:00",
  "end": "2026-10-27T12:00:00-04:00",
  "timezone": "America/Toronto",
  "hours": 4,
  "date": null,
  "bucket_minutes": 1,
  "unit": "°C",
  "points": [
    { "time": "2026-10-27T08:00:00-04:00", "average": 22.41, "minimum": 22.3, "maximum": 22.5,
      "count": 2, "suspicious_count": 0 }
  ],
  "statistics": { "minimum": 21.9, "maximum": 23.4, "average": 22.6, "count": 236, "trend": "rising" }
}
```

- Une observation appartient à la période selon `observed_at`, ou
  `received_at` si l'horodatage capteur est absent ; borne de fin exclue.
- Les créneaux sont alignés sur l'heure locale (minuit pour 1 jour).
- `unit` est l'unité canonique (`°C`, `%`, `dBA`, `personnes`, `ppm`).
- `trend` compare le premier et le dernier créneau à une tolérance propre à
  chaque mesure.

Erreurs 400, par exemple :

```json
{ "detail": "La période demandée dépasse la limite de 31 jours.",
  "errors": { "end": ["La période demandée dépasse la limite de 31 jours."] } }
```

## Règles d'alarme

Voir [`alarms.md`](alarms.md) pour la sémantique.

| Méthode | Chemin | Accès |
|---|---|---|
| `GET` | `/api/alarm-rules/?zone=<code>\|all&metric=<type>&enabled=true\|false` | public |
| `GET` | `/api/alarm-rules/metadata/` | public |
| `GET` | `/api/alarm-rules/<id>/` | public |
| `POST` | `/api/alarm-rules/` | libre |
| `PATCH` | `/api/alarm-rules/<id>/` | libre |
| `DELETE` | `/api/alarm-rules/<id>/` | libre |

Filtre `zone=<code>` : règles de cette zone **et** règles globales ;
`zone=all` : règles globales uniquement.

### Représentation

```json
{
  "id": 3,
  "name": "Niveau sonore élevé",
  "description": "",
  "zone": null,
  "zone_name": null,
  "metric": "sound_level",
  "operator": "gte",
  "threshold": 50.0,
  "threshold_high": null,
  "unit": "dBA",
  "condition_label": "≥ 50 dBA",
  "enabled": true,
  "severity": "warning",
  "min_duration_seconds": 0,
  "hysteresis": 0.0,
  "active_alerts": 0,
  "created_at": "…", "updated_at": "…", "created_by": "gestion", "updated_by": "gestion"
}
```

Champs modifiables : `name`, `description`, `zone` (code ou `null` = toutes
les zones), `metric`, `operator` (`gt`, `gte`, `lt`, `lte`, `outside_range`,
`inside_range`), `threshold`, `threshold_high` (intervalles uniquement),
`enabled`, `severity` (`info`, `warning`, `critical`),
`min_duration_seconds` (0–86 400), `hysteresis` (≥ 0). Lecture seule :
`unit`, `condition_label`, `active_alerts`, métadonnées.

### Validation (400)

- `name` non vide ; `metric` connu ; `operator` autorisé pour la mesure ;
- intervalles : `threshold_high` obligatoire et > `threshold` ; seuil simple :
  `threshold_high` doit être absent ou `null` (un passage d'intervalle à seuil
  simple l'efface automatiquement) ;
- seuils dans les limites physiques de la mesure (ex. 0–100 % pour
  l'humidité) ; entiers pour `occupancy` ;
- `hysteresis` ≥ 0, entière pour `occupancy`, et inférieure à la moitié de
  l'intervalle pour `outside_range`.

### Effets des modifications

| Action | Effet sur les alertes en cours de la règle |
|---|---|
| `PATCH {"enabled": false}` | résolues (`resolution: "rule_disabled"`) |
| `PATCH` d'un champ de condition (`zone`, `metric`, `operator`, seuils, durée, hystérésis) | résolues (`"rule_updated"`) ; réévaluation à la prochaine mesure |
| `PATCH {"severity": …}` | gravité mise à jour |
| `DELETE` | résolues (`"rule_deleted"`), puis règle supprimée |

### `GET /api/alarm-rules/metadata/`

Catalogue utilisé par le formulaire : `metrics` (clé, libellé, unité,
`integer`, `min`, `max`, opérateurs), `operators` (clé, libellé, symbole,
`range`), `severities`, `max_duration_seconds`.

## Alertes et événements

### `GET /api/alerts/`

Chaque alerte est un épisode : déclenchement puis éventuelle résolution. C'est
l'historique des événements d'alarme (règles) et des alertes de qualité des
données (`rule: null`, code `DATA_QUALITY_<TYPE>`).

| Paramètre | Description |
|---|---|
| `active` | `true` / `false` |
| `zone` | code de zone |
| `rule` | identifiant de règle |
| `severity` | `info`, `warning`, `critical` |
| `since`, `until` | bornes ISO 8601 sur `created_at` |
| `limit` | 1–1 000 (défaut 500) ; tri du plus récent au plus ancien |

```json
{
  "id": 4,
  "zone": 4, "zone_code": "meeting-room", "zone_name": "Salle de réunion",
  "observation": 23631,
  "rule": 5, "rule_name": "Salle de réunion trop chaude",
  "code": "RULE_5",
  "message": "Salle de réunion trop chaude — Salle de réunion : 24,9 °C (condition > 20,5 °C)",
  "severity": "warning",
  "trigger_value": 24.9,
  "created_at": "2026-10-27T16:07:20-04:00",
  "resolved_at": "2026-10-27T16:07:26-04:00",
  "resolution": "rule_disabled",
  "active": false
}
```

`resolution` : `returned_to_normal`, `rule_disabled`, `rule_updated`,
`rule_deleted`, `migrated`, ou vide. `observation` pointe vers la dernière
mesure ayant maintenu l'alerte. Si la règle est supprimée, `rule` devient
`null` mais `code` (`RULE_<id>`) et `message` restent.

## Confort thermique

Méthode et valeurs par défaut : [`comfort-energy.md`](comfort-energy.md).

### `GET /api/comfort/current/`

Chaque zone active, ses plages de confort applicables et sa dernière évaluation
(`null` tant qu'aucune mesure n'a été évaluée).

```json
{
  "zone_code": "meeting-room",
  "zone_name": "Salle de réunion",
  "zone_type": "meeting_room",
  "customized": false,
  "profile": { "temperature_min": 20, "temperature_max": 24, "temperature_tolerance": 2,
               "humidity_min": 30, "humidity_max": 60, "humidity_tolerance": 10 },
  "assessment": { "assessed_at": "…", "temperature": 25.0, "humidity": 45.0,
                  "temperature_status": "warm", "humidity_status": "ok",
                  "level": "acceptable", "score": 82.5 }
}
```

`level` : `comfortable`, `acceptable`, `uncomfortable`, `unknown`.
`temperature_status` : `ok`, `cool`, `too_cold`, `warm`, `too_hot`, `unknown` ;
`humidity_status` : `ok`, `dry`, `too_dry`, `humid`, `too_humid`, `unknown`.

### `GET /api/comfort/zones/<code>/history/`

Paramètres de période identiques à l'historique des mesures (`start`, `end`,
`bucket_minutes`, ou `hours`, `date`).

```json
{
  "zone_code": "meeting-room", "start": "…", "end": "…", "bucket_minutes": 5,
  "profile": { "…": "…" },
  "points": [ { "time": "…", "score": 91.2, "temperature": 23.1, "humidity": 44.0,
                "comfortable": 3, "acceptable": 1, "uncomfortable": 0 } ],
  "summary": { "count": 72, "average_score": 93.4, "comfortable_ratio": 0.82,
               "acceptable_ratio": 0.18, "uncomfortable_ratio": 0.0 }
}
```

Les compteurs et proportions portent sur le nombre d'évaluations.

### `/api/comfort/profiles/`

| Méthode | Chemin | Effet |
|---|---|---|
| `GET` | `/api/comfort/profiles/` | plages de chaque zone (sans évaluation) |
| `GET` | `/api/comfort/profiles/<code>/` | plages d'une zone |
| `PATCH` | `/api/comfort/profiles/<code>/` | personnalise (champs absents : valeur actuelle) |
| `DELETE` | `/api/comfort/profiles/<code>/` | rétablit les valeurs par défaut (réponse 200 avec ces valeurs) |

Validation : température −20 à 60 °C, humidité 0 à 100 %, tolérances
strictement positives (≤ 20 °C, ≤ 50 %), minimum < maximum.

## Énergie

Estimation par modèle, aucune mesure de consommation :
[`comfort-energy.md`](comfort-energy.md).

### `GET /api/energy/summary/`

Période : mêmes paramètres que l'historique (défaut : 24 dernières heures).
Un intervalle est compté dans la période qui contient sa fin.

```json
{
  "start": "…", "end": "…",
  "total": { "lighting_kwh": 7.1, "equipment_kwh": 36.1, "heating_kwh": 2.3, "cooling_kwh": 4.6,
             "total_kwh": 50.1, "covered_hours": 6.0, "average_power_w": 8341.2 },
  "zones": [ { "zone_code": "server-equipment-room", "zone_name": "…", "zone_type": "server_room",
               "customized": false, "total_kwh": 29.3, "…": "…" } ]
}
```

`covered_hours` : durée réellement estimée ; `average_power_w` : énergie ÷
durée estimée (`null` sans estimation).

### `GET /api/energy/zones/<code>/series/`

```json
{ "zone_code": "…", "start": "…", "end": "…", "bucket_minutes": 15,
  "points": [ { "time": "…", "lighting_kwh": 0.03, "equipment_kwh": 0.07,
                "heating_kwh": 0.01, "cooling_kwh": 0.0, "total_kwh": 0.11 } ],
  "total": { "…": "…" } }
```

### `/api/energy/profiles/`

Mêmes méthodes que les plages de confort. Champs et bornes :

| Champ | Unité | Bornes |
|---|---|---|
| `floor_area_m2` | m² | 0 à 10 000 |
| `lighting_w_per_m2` | W/m² | 0 à 50 |
| `equipment_base_w` | W | 0 à 1 000 000 |
| `equipment_w_per_person` | W | 0 à 5 000 |
| `default_occupancy` | personnes (entier) | 0 à 500 |
| `envelope_ua_w_per_k` | W/K | 0 à 100 000 |
| `ventilation_l_s_per_person` | L/s | 0 à 100 |
| `outdoor_temperature_c` | °C | −50 à 50 |
| `heating_cop`, `cooling_cop` | — | 0,5 à 10 |

## Santé

### `GET /api/health/`

```json
{ "status": "ok", "database": "connected", "channel_layer": "RedisChannelLayer",
  "event_bus": "kafka", "timestamp": "2026-10-27T20:04:33+00:00" }
```

503 avec `"status": "degraded"` si la base ne répond pas.

## WebSocket

### `/ws/dashboard/`

Messages envoyés par le serveur :

| Message | Quand |
|---|---|
| `{"event": "realtime.connected"}` | à l'ouverture |
| `{"event": "observation.created", "data": {…}}` | chaque nouvelle observation validée (même forme que `/api/observations/`, plus `zone_code`) |
| `{"event": "alerts.changed"}` | une alerte a été créée, résolue ou modifiée — recharger `/api/alerts/?active=true` |
| `{"event": "comfort.updated", "data": {…}}` | nouvelle évaluation de confort (`zone_code` + champs de `assessment`) |
| `{"event": "energy.updated", "data": {"zone_code": "…"}}` | nouvel intervalle d'énergie estimé — recharger le bilan |

### `/ws/zones/<code>/`

Observations et évaluations de confort d'une seule zone (`observation.created`, `comfort.updated`).
