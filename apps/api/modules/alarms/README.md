# Module Alarms

Règles d'alarme configurables (CRUD), évaluation de chaque mesure persistée
(machine à états avec durée minimale et hystérésis), alertes de qualité des
données et consultation des alertes. Les décisions sont publiées ; le module
Database les enregistre.

## Contrat

| | |
|---|---|
| HTTP | `/api/alarm-rules/` (GET, POST, PATCH, DELETE ; `metadata/`), `/api/alerts/` (filtres `active`, `zone`, `rule`, `severity`, `since`, `until`, `limit`) |
| Kafka entrée | `database.events` : `observation.persisted`, `alarm_rule.changed` |
| Kafka sortie | `alarms.events` : `alert.raised`, `alert.resolved`, `alarm_state.saved`, `alarm_rule.reset`, `alarm_rule.severity_propagated` |
| Commandes | `alarms.commands` : `alarm_rule.create`, `alarm_rule.update`, `alarm_rule.delete` (réponse attendue sur `database.replies`) |
| Données lues | règles, alertes, états d'évaluation |
| Détails | `docs/alarms.md`, `docs/events.md` |

## Structure

```text
core/
  domain/     AlarmRuleValidator, ConditionEvaluator, AlarmStateMachine, RuleChangePolicy,
              AlertMessageBuilder, RefreshThrottle, AlarmStatus, RuleState…
  ports/      AlarmRuleReader, AlertReader, RuleCommands, RuleStates,
              QualityAlertStates, AlarmEventsPublisher
  services/   RuleEvaluationService, QualityAlertService, RuleChangeService,
              AlarmRuleService, AlarmRuleCatalogService, AlertQueryService
adapters/
  http/          contrôleurs DRF, serializers, urls.py
  messaging/     AlarmsConsumer, AlarmEventsProducer, RuleCommandGateway (commande corrélée)
  persistence/   repositories ORM, RuleStateStore et QualityAlertStore (vues locales)
composition.py   alarm_rule_service(), alert_query_service(), alarms_consumer()…
```

## Réutiliser le module

Le moteur (`core/domain`) et les services sont indépendants de Django et de
Kafka : un autre projet fournit les six ports (par exemple un dépôt SQL et un
publieur MQTT). Dans un projet Django, ajouter `modules.alarms.apps.AlarmsConfig`,
inclure `modules.alarms.adapters.http.urls` et lancer `run_consumers`.
