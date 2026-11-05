# Topics et événements Kafka

Tous les noms de topics sont configurables (voir `apps/api/.env.example`).

## Topics

| Topic (défaut) | Producteur | Consommateurs | Clé |
|---|---|---|---|
| `gridd.obs.environmental.temperature`, `…humidity`, `…co2`, `gridd.obs.acoustic.sound_level`, `gridd.obs.occupancy.count` | capteurs, simulateur | `ingestion` (connexion `sensors`) | nœud |
| `gridd.backend.ingestion.observations` | `ingestion` | `database` | zone |
| `gridd.backend.alarms.events` | `alarms` | `database` | zone ou `rule:<id>` |
| `gridd.backend.alarms.commands` | `alarms` (API) | `database` | `rule:<id>` |
| `gridd.backend.comfort.events` | `comfort` | `database` | zone |
| `gridd.backend.comfort.commands` | `comfort` (API) | `database` | zone |
| `gridd.backend.energy.events` | `energy` | `database` | zone |
| `gridd.backend.energy.commands` | `energy` (API) | `database` | zone |
| `gridd.backend.database.events` | `database` | `alarms`, `comfort`, `energy`, `realtime` | zone ou `rule:<id>` |
| `gridd.backend.database.replies` | `database` | émetteur de la commande | `correlation_id` |

Les topics lus par `database` sont fixés par `DATABASE_SUBSCRIBED_TOPICS`.
`run_consumers` crée les topics internes manquants si
`KAFKA_AUTO_CREATE_TOPICS=true` (`KAFKA_TOPIC_PARTITIONS`,
`KAFKA_TOPIC_REPLICATION_FACTOR`).

## Message capteur

Inchangé par rapport à la version précédente :

```json
{
  "node_id": "environmental-node01",
  "type": "temperature",
  "value": 22.4,
  "unit": "C",
  "timestamp": "2026-10-27T08:00:00-04:00",
  "metadata": { "zone": { "id": "professors-office", "label": "Bureau des professeurs" } }
}
```

`nodeId`, `observed_at` et `observedAt` sont aussi acceptés. Sans horodatage,
celui du broker est utilisé. Un message invalide est journalisé puis ignoré.

## Enveloppe des événements internes

```json
{
  "type": "observation.validated",
  "payload": { "…": "…" },
  "source": "ingestion",
  "event_id": "6c1d…",
  "occurred_at": "2026-11-04T19:58:02.103+00:00",
  "correlation_id": null,
  "reply_to": null
}
```

`correlation_id` et `reply_to` ne sont renseignés que pour les commandes.

## Catalogue

### `ingestion` → `database`

**`observation.validated`**

```json
{
  "event_id": "uuid (stable pour un message Kafka donné)",
  "node_id": "environmental-node01", "metric": "temperature",
  "value": 22.4, "unit": "C",
  "observed_at": "ISO 8601 | null", "received_at": "ISO 8601",
  "metadata": { "zone": {…}, "_kafka": {…}, "timestamp_source": "payload" },
  "sensor_metadata": { "zone": {…} },
  "quality_status": "normal | suspicious | invalid", "quality_reason": "",
  "zone": { "code": "professors-office", "name": "Bureau des professeurs", "type": "office | null" }
}
```

### `alarms` → `database`

| Type | Contenu | Effet |
|---|---|---|
| `alert.raised` | `zone_code`, `code`, `rule_id`, `severity`, `message`, `trigger_value`, `observation_id`, `refresh_fields` | ouvre l'alerte, ou met à jour les champs `refresh_fields` de l'alerte active |
| `alert.resolved` | `zone_code`, `code`, `resolution`, `observation_id` | clôt l'alerte active |
| `alarm_state.saved` | `rule_id`, `zone_code`, `status`, `pending_since`, `last_value`, `last_observed_at` | enregistre l'état (règle, zone) |
| `alarm_rule.reset` | `rule_id`, `alert_code`, `resolution` | clôt les alertes de la règle et efface ses états |
| `alarm_rule.severity_propagated` | `rule_id`, `alert_code`, `severity` | reporte la gravité sur les alertes actives |

### Commandes (réponse attendue)

| Type | Topic | Contenu | Réponse `data` |
|---|---|---|---|
| `alarm_rule.create` | `alarms.commands` | `fields`, `user_id` | `rule_id` |
| `alarm_rule.update` | `alarms.commands` | `rule_id`, `fields`, `user_id` | `rule_id`, `changed_fields` |
| `alarm_rule.delete` | `alarms.commands` | `rule_id` | `rule_id` |
| `comfort_profile.save` | `comfort.commands` | `zone_code`, `profile` (6 champs) | `zone_code` |
| `comfort_profile.reset` | `comfort.commands` | `zone_code` | `zone_code` |
| `energy_profile.save` | `energy.commands` | `zone_code`, `profile` (10 champs) | `zone_code` |
| `energy_profile.reset` | `energy.commands` | `zone_code` | `zone_code` |

`fields` désigne la zone par son code (`null` = toutes les zones).

### `comfort` et `energy` → `database`

**`comfort.assessed`** (topic `comfort.events`) : `zone_code`,
`observation_id`, `assessed_at`, `temperature`, `humidity`,
`temperature_status`, `humidity_status`, `level`, `score`.

**`energy.estimated`** (topic `energy.events`) : `zone_code`,
`observation_id` (mesure qui clôt l'intervalle), `start`, `end`,
`duration_seconds`, `indoor_temperature`, `occupancy`, `occupancy_source`
(`sensor` ou `profile`), `hvac_estimated`, `lighting_wh`, `equipment_wh`,
`heating_wh`, `cooling_wh`, `total_wh`.

Les deux sont idempotents : une seconde livraison pour la même observation
est ignorée.

Réponses sur `database.replies` :

- `command.succeeded` : `{"data": {…}}` ;
- `command.failed` : `{"error": {"code": "not_found | invalid | error", "message": "…", "errors": {"champ": ["…"]}}}`.


### `database` → modules

| Type | Contenu | Consommateurs |
|---|---|---|
| `observation.persisted` | observation enregistrée (`id`, `zone`, `zone_code`, `zone_name`, `sensor`, `sensor_node_id`, `type`, `value`, `unit`, `observed_at`, `received_at`, `quality_status`, `quality_reason`, `metadata`) | `alarms`, `realtime` |
| `alerts.changed` | `zone_code` (ou `null`) | `realtime` |
| `alarm_rule.changed` | `rule_id`, `action` (`created`, `updated`, `deleted`), `changed_fields`, `enabled`, `severity` | `alarms` |
| `comfort.persisted` | évaluation enregistrée (`id`, `zone_name` + champs de `comfort.assessed`) | `realtime` |
| `energy.persisted` | `id`, `zone_code`, `end`, `total_wh` | `realtime` |

`observation.persisted` est relayé tel quel aux navigateurs
(`{"event": "observation.created", "data": …}` sur `/ws/dashboard/`).
