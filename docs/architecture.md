# Architecture

## Vue d'ensemble

GRIDD est composé de deux applications déployées séparément :

```text
                ┌────────────────────────── apps/api ──────────────────────────┐
Kafka GRIDD ───►│ consume_kafka ─┐                                             │
Simulateur  ───►│ simulate_gridd ┴► services.ingest_observation                │
                │                    ├─ contrôle de qualité (alertes DATA_…)   │
                │                    ├─ alarm_engine.evaluate_alarm_rules       │
                │                    └─ realtime (Redis) ─► WebSocket          │
                │ PostgreSQL ◄── modèles      API REST /api/ ◄── DRF            │
                └───────────────────────────────▲──────────────────────────────┘
                                                │ HTTPS + WSS (CORS, jeton)
                ┌──────────────── web ──────────┴──────────────────────────────┐
                │ Navigateur : React (vues → composables/stores → services     │
                │              → requests)                                      │
                │ Serveur Node : fichiers statiques + /env.js + /healthz        │
                └──────────────────────────────────────────────────────────────┘
```

Aucune logique métier de l'API n'est dupliquée dans le frontend : il ne fait
que valider les saisies pour un retour immédiat, l'API restant l'autorité
(validation, droits, évaluation des alarmes).

## État initial et problèmes corrigés

| Constat avant la refonte | Correction |
|---|---|
| `App.tsx` (~1 200 lignes) et `correlations.tsx` mêlaient routage, HTTP, état, calculs et rendu | Découpage en `routes/`, `views/`, `components/`, `composables/`, `stores/`, `services/`, `requests/`, `resources/`, `utils/` |
| Mesures disponibles déduites du **nom** des zones (`zone.name === "Salle de réunion"`), compteurs 6/4/1 codés en dur | L'API expose `zone.metrics` (capteurs actifs) ; les compteurs en sont dérivés |
| Vite compilait vers `gridd_django/static/` ; vues Django `/`, `/legacy/`, `/zones/<code>/` dont les gabarits avaient été supprimés (5 tests en échec) | Frontend autonome dans `web/` ; vues gabarits retirées du backend |
| Dockerfile/Compose du frontend copiés d'un autre projet ; serveur Node important un module absent | Dockerfile multi-étapes, Compose et serveur Node réécrits et testés |
| `migrate` exécuté pendant la construction de l'image API, image en root | Migrations au démarrage (`RUN_MIGRATIONS`), utilisateur non privilégié |
| Historique limité à 1 h / 6 h / 24 h / 7 j ou à un jour | Contrat `start`/`end`/`bucket_minutes` validé côté serveur |
| Seuils d'alarme figés dans `ThresholdProfile`, éditables uniquement dans l'admin, évaluation codée par type | Règles `AlarmRule` configurables depuis l'interface, moteur générique |
| API entièrement anonyme | Authentification par jeton et permissions par modèle pour les écritures |
| WebSocket limité aux hôtes de l'API (refus d'un frontend sur un autre domaine), pas de CORS | `OriginValidator` + `django-cors-headers` configurables |
| `"latest"` pour toutes les dépendances, deux lockfiles | Versions exactes, `package-lock.json` seul |

## Backend (`apps/api`)

Une seule application Django, `core`, organisée par responsabilité :

| Module | Responsabilité |
|---|---|
| `metrics.py` | Catalogue des mesures : unités acceptées et canoniques, limites physiques, tolérance de tendance, nature (comptage) et opérateurs autorisés. Ajouter un paramètre = ajouter une entrée. |
| `services.py` | `ingest_observation` : point d'entrée unique de l'ingestion (Kafka, simulateur), dans une transaction. |
| `alarm_engine.py` | Évaluation des règles (fonctions pures + persistance des états), effets des modifications de règles. |
| `history.py` | Analyse des paramètres de période, choix de la granularité, agrégation par créneaux locaux. |
| `api.py`, `alarm_api.py`, `auth_api.py` | Vues REST. |
| `permissions.py`, `authentication.py`, `exceptions.py` | Droits, jetons expirants, format d'erreur uniforme. |
| `realtime.py`, `consumers.py` | Diffusion Channels et WebSocket. |

Dépendances : `api` → `services`/`history`/`alarm_engine` → `models` → `metrics`.
`alarm_engine` n'importe pas `services` (pas de cycle).

### Décisions

- **Une alerte = un épisode.** Le modèle `Alert` existant sert d'historique des
  déclenchements (`created_at`, `trigger_value`, `resolved_at`, `resolution`,
  `rule`) : l'endpoint `/api/alerts/` existant est réutilisé plutôt que de créer
  un `/alarms/events` en doublon.
- **Les seuils de `ThresholdProfile` sont convertis en règles** par une
  migration (0012) puis retirés (0013), pour n'avoir qu'une source de vérité.
  Le profil ne garde que les paramètres de qualité des données.
- **Les mesures invalides n'alimentent pas les règles** : elles sont déjà
  signalées par une alerte de qualité ; une valeur physiquement impossible ne
  doit pas déclencher, par exemple, « température trop élevée ».
- **Lecture publique conservée** : le tableau de bord était consultable sans
  compte ; seules les écritures exigent une authentification.
- **Jeton plutôt que session** : frontend et API sont sur des origines
  différentes ; un en-tête `Authorization` évite cookies inter-domaines et CSRF.

## Frontend (`web`)

| Dossier | Responsabilité |
|---|---|
| `routes/` | `definitions.ts` : nom, chemin, métadonnées (titre, libellé de navigation), règle d'accès ; `index.tsx` associe les vues ; `RouteGuard` applique titre et accès. |
| `layouts/` | `AppLayout` : en-tête, navigation, erreur globale, contenu. |
| `views/` | Un écran par route ; assemble les composants et coordonne les composables. |
| `components/` | Composants de présentation sans appel réseau (sous-dossiers `common`, `layout`, `measurements`, `charts`, `forms`, `alarms`). |
| `composables/` | Hooks réutilisables : `useAsyncData` (chargement/erreur/annulation), `useObservationPeriod` (période + URL + actualisation), `useHistoryFilters`, `useZoneHistory`, `useCorrelationSeries`, `useAlarmRules`. |
| `stores/` | États réellement partagés : `authStore` (session) et `dashboardStore` (zones, dernières mesures, alertes actives, temps réel, alertes consultées). |
| `services/` | Opérations fonctionnelles par ressource (`historyService`, `alarmRulesService`…). |
| `requests/` | `httpClient` (URL de base, en-têtes, jeton, délai, JSON, `ApiError`), `config` (adresse API), `realtimeSocket` (WebSocket avec reconnexion). |
| `resources/` | Types alignés sur le contrat de l'API et validation des saisies (`alarmRule`, `period`, `auth`). |
| `utils/`, `constants/`, `types/` | Fonctions pures, valeurs communes, types transversaux. |

Flux d'une donnée : `View` → `composable` → `service` → `requests/httpClient`
→ API. Les erreurs remontent sous forme d'`ApiError` (message lisible + erreurs
par champ) et sont affichées par `ErrorMessage` ou associées aux champs.

### Temps réel

`dashboardStore` combine un chargement complet toutes les 60 s (filet de
sécurité) et le WebSocket `/ws/dashboard/` : `observation.created` met à jour
les dernières mesures, `alerts.changed` recharge les alertes actives.

## Évolutivité

- **Nouveau paramètre mesuré** : choix dans `Sensor.SensorType`, entrée dans
  `core/metrics.py`, topic Kafka ; côté frontend, entrée dans
  `constants/metrics.ts` (libellé, icône, couleur). Les règles d'alarme, les
  historiques et les cartes d'espace l'utilisent automatiquement.
- **Nouvel opérateur** : `metrics.py` + `condition_met`/`back_to_normal`
  dans `alarm_engine.py`.
- **Nouvel écran** : entrée dans `routes/definitions.ts` et vue dans `views/`.
