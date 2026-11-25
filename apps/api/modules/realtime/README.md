# Module Realtime

Pousse aux navigateurs les faits persistés (mesures, prédictions, météo,
alertes, zones) par WebSocket. À la connexion, `/ws/dashboard/` envoie un
instantané complet : le tableau de bord ne fait aucun appel HTTP périodique.

## Contrat

| | |
|---|---|
| Kafka entrée | `database.events` : `observation.persisted`, `climate_prediction.persisted`, `weather_snapshot.persisted`, `alerts.changed`, `zones.changed` |
| WebSocket | `/ws/dashboard/` (instantané, `{"action": "snapshot"}`, `{"action": "ping"}`), `/ws/zones/<code>/` |
| Réglages | `REALTIME_ALERT_HISTORY_DAYS`, `REALTIME_ALERT_HISTORY_LIMIT`, `CHANNEL_LAYERS` |

## Structure

```text
core/
  domain/     RealtimeGroups (noms des groupes de diffusion)
  ports/      Broadcaster, DashboardSnapshots, DashboardReader, DashboardPresenter
  services/   RealtimeRelayService (validation, regroupement par lot, rattrapage)
              DashboardSnapshotService (instantané, alertes, zones)
adapters/
  messaging/realtime_consumer.py       abonnement Kafka → RealtimeRelayService
  websocket/                           consommateurs Channels, routing.py,
                                       RealtimeBroadcaster (Broadcaster via channel layer)
  persistence/                         DashboardRepository, DashboardPayloadMapper
composition.py                         dashboard_snapshot_service(), realtime_consumer()
```

## Réutiliser le module

`RealtimeRelayService` ne dépend que de `Broadcaster` (Channels, SSE,
Socket.IO…) et de `DashboardSnapshots`. Dans un projet Django/Channels :
ajouter `modules.realtime.apps.RealtimeConfig` et brancher
`modules.realtime.adapters.websocket.routing.websocket_urlpatterns` dans
`asgi.py`.
