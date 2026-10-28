# GRIDD — Frontend

Interface web de GRIDD : vue d'ensemble, espaces, analyse historique avec
périodes d'observation configurables, alertes et gestion des règles d'alarme.

- React 19 + TypeScript, compilé par Vite 8 ;
- React Router 7 (routes déclarées dans `src/routes/`) ;
- Recharts pour les graphiques, lucide-react pour les icônes ;
- serveur de production Node.js sans dépendance (`server/`).

L'application est **indépendante de l'API** : elle se construit et démarre sans
le backend ; seules les données affichées en dépendent.

## Commandes

| Commande | Effet |
|---|---|
| `npm ci` | Installe les dépendances exactes de `package-lock.json` |
| `npm run dev` | Serveur de développement Vite sur <http://localhost:5173> (relaie `/api` et `/ws` vers `VITE_DEV_API_PROXY`) |
| `npm run build` | Compile l'application (`dist/`) et le serveur Node (`dist-server/`) |
| `npm start` | Sert le build avec le serveur Node (`PORT`, défaut 3000) |
| `npm run typecheck` | Vérification TypeScript de l'application, des tests et du serveur |
| `npm test` | Tests Vitest (vues, routes, formulaires, services, serveur) |

Node.js 20.19+ ou 22.12+ est requis (exigence de Vite 8).

## Configuration

Copier `.env.example` en `.env`. **Toutes ces valeurs sont publiques** (elles
finissent dans le navigateur) : n'y placer aucun secret.

| Variable | Lue par | Rôle |
|---|---|---|
| `GRIDD_API_URL` | serveur Node, au démarrage | Adresse de l'API vue par le navigateur (ex. `https://api.gridd.example.org`). Vide = même origine. |
| `GRIDD_WS_URL` | serveur Node, au démarrage | Adresse WebSocket. Vide = déduite de `GRIDD_API_URL` (`https`→`wss`). |
| `PORT` / `HOST` | serveur Node | Écoute (défaut `3000` / `0.0.0.0`). |
| `LOG_REQUESTS` | serveur Node | `true` pour journaliser chaque requête. |
| `WEB_PORT` | Docker Compose | Port publié sur l'hôte. |
| `VITE_DEV_API_PROXY` | `npm run dev` | API cible du proxy de développement (défaut `http://127.0.0.1:8000`). |
| `VITE_API_URL`, `VITE_WS_URL` | compilation | Valeurs de repli **intégrées au bundle** ; la configuration d'exécution reste prioritaire. |

### Configuration d'exécution

Le serveur Node génère `/env.js` au démarrage :

```js
window.__GRIDD_CONFIG__ = { "API_URL": "https://api.gridd.example.org" };
```

`index.html` charge ce script avant l'application ; `src/requests/config.ts`
le lit en priorité. Une même image Docker peut ainsi viser n'importe quelle API
sans recompilation. Seules `GRIDD_API_URL` et `GRIDD_WS_URL` sont exposées
(liste blanche dans `server/app.ts`).

Si le frontend et l'API sont sur des domaines différents, l'origine du frontend
doit figurer dans `CORS_ALLOWED_ORIGINS` côté API (REST et WebSocket).

## Organisation du code

```text
src/
├── main.tsx, App.tsx      # point d'entrée, fournisseurs d'état, routeur
├── routes/                # table des routes (nom, chemin, métadonnées, accès) et garde
├── layouts/               # AppLayout : en-tête, navigation, contenu
├── views/                 # écrans : Overview, Spaces, History, Alerts, AlarmRules,
│                          #   AlarmRuleEdit, Login, NotFound
├── components/
│   ├── common/            # éléments génériques (messages, en-têtes, cartes)
│   ├── layout/            # barre supérieure, navigation
│   ├── measurements/      # tuiles de mesure, cartes d'espace
│   ├── charts/            # courbe d'historique, statistiques, corrélations
│   ├── forms/             # sélecteur de période, formulaire de règle, connexion
│   └── alarms/            # alerte active, liste des règles
├── composables/           # hooks : chargement asynchrone, période, filtres, règles
├── stores/                # états partagés : authentification, tableau de bord
├── services/              # opérations fonctionnelles (une par ressource API)
├── requests/              # client HTTP, configuration API, WebSocket
├── resources/             # types des ressources API et validation
├── utils/                 # fonctions pures (formatage, périodes, statistiques)
├── constants/             # libellés, couleurs, périodes, repères
├── types/                 # types transversaux
└── styles/                # global.css (existant) + features.css (ajouts)
```

Règles de dépendance : `views` → `components`, `composables`, `stores` ;
`composables`/`stores` → `services` → `requests`. Les composants n'appellent
jamais l'API ; seul `requests/httpClient.ts` utilise `fetch`. Détails dans
[`../docs/architecture.md`](../docs/architecture.md).

## Docker

```bash
cp .env.example .env          # renseigner GRIDD_API_URL
docker compose build
docker compose up -d
docker compose logs -f
docker compose down
```

- Image en deux étapes : `npm ci` + build, puis image `node:22-alpine` ne
  contenant que `dist/`, `dist-server/` et `package.json` ;
- exécution sous l'utilisateur non privilégié `node`, port 3000 ;
- contrôle de santé `GET /healthz` ;
- aucun secret ni `.env` copié dans l'image (`.dockerignore`).

Voir [`../docs/deployment.md`](../docs/deployment.md).

## Routes

| Chemin | Vue | Accès |
|---|---|---|
| `/` | Vue d'ensemble | public |
| `/spaces` | Espaces | public |
| `/history?zone=&metric=&period=` ou `&start=&end=` | Analyse historique | public |
| `/alerts` | Alertes actives, règles d'un espace, historique | public |
| `/alarms/rules` | Règles d'alarme (lecture) | public |
| `/alarms/rules/new` | Création d'une règle | permission `alarm_rules.add` |
| `/alarms/rules/:ruleId/edit` | Modification | permission `alarm_rules.change` |
| `/login?next=` | Connexion | public |

Le serveur Node renvoie `index.html` pour tout chemin sans extension, ce qui
permet de recharger n'importe quelle page.
