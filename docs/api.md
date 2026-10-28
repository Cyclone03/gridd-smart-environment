# Contrat de l'API

Base : `GRIDD_API_URL` (ex. `https://api.gridd.example.org`). Toutes les
réponses sont en JSON ; les dates suivent ISO 8601 avec décalage horaire,
exprimées dans le fuseau du serveur (`TIME_ZONE`, défaut `America/Toronto`).

## Généralités

### Authentification

- Les requêtes `GET` sont publiques.
- Les écritures exigent l'en-tête `Authorization: Token <clé>` obtenu par
  `POST /api/auth/token/`. Le jeton expire après `AUTH_TOKEN_TTL_HOURS`
  (12 h par défaut) et est remplacé à chaque connexion.
- Les droits sur les règles d'alarme sont les permissions Django
  `core.add_alarmrule`, `core.change_alarmrule`, `core.delete_alarmrule`.

### Format des erreurs

```json
{ "detail": "Message lisible", "errors": { "champ": ["message", "…"] } }
```

`errors` n'est présent que pour les erreurs de validation (400).

| Code | Signification |
|---|---|
| 400 | Paramètres ou données invalides (`errors` par champ) |
| 401 | Authentification absente, invalide ou expirée |
| 403 | Authentifié mais sans la permission requise |
| 404 | Ressource inconnue |
| 405 | Méthode non disponible (ex. `PUT` sur une règle) |
| 429 | Trop de tentatives de connexion |
| 503 | `GET /api/health/` : base de données indisponible |

### CORS et WebSocket

Les origines listées dans `CORS_ALLOWED_ORIGINS` peuvent appeler l'API depuis
un navigateur. Les WebSocket acceptent ces mêmes origines ainsi que les hôtes de
`ALLOWED_HOSTS` ; toute autre origine reçoit un refus 403.

## Authentification

### `POST /api/auth/token/`

```json
{ "username": "gestion", "password": "…" }
```

Réponse 200 :

```json
{
  "token": "…",
  "expires_at": "2026-10-28T08:16:54+00:00",
  "user": {
    "username": "gestion",
    "display_name": "Gestion Alarmes",
    "is_staff": false,
    "permissions": { "alarm_rules": { "add": true, "change": true, "delete": true } }
  }
}
```

Erreurs : 400 (champ manquant), 401 « Identifiant ou mot de passe
incorrect. », 429 au-delà de `LOGIN_THROTTLE_RATE` (10/min par IP).

### `GET /api/auth/me/` — utilisateur courant (401 sans jeton valide)

### `POST /api/auth/logout/` — révoque le jeton (204)

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
| `POST` | `/api/alarm-rules/` | `core.add_alarmrule` |
| `PATCH` | `/api/alarm-rules/<id>/` | `core.change_alarmrule` |
| `DELETE` | `/api/alarm-rules/<id>/` | `core.delete_alarmrule` |

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

## Santé

### `GET /api/health/`

```json
{ "status": "ok", "database": "connected", "channel_layer": "RedisChannelLayer",
  "timestamp": "2026-10-27T20:04:33+00:00" }
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

### `/ws/zones/<code>/`

Observations d'une seule zone (`observation.created`).
