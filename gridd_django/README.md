# GRIDD Smart Environment

Plateforme de supervision environnementale du GRIDD. Le backend Django reçoit
les observations Kafka, les conserve dans PostgreSQL et les diffuse en temps
réel au dashboard React avec Django Channels et Redis.

## Architecture

```text
Kafka GRIDD ─┐
             ├─> Django ─> PostgreSQL ─> API REST ─┐
Simulateur ──┘       └─> Redis / WebSocket ────────┼─> Dashboard React
                                                   └─> Alertes et historique
```

Le dépôt contient deux applications :

```text
gridd_django_project/
├── frontend/       # React, TypeScript, Vite et Recharts
└── gridd_django/   # Django, API REST, Channels et ingestion Kafka
```

## Prérequis

Pour une installation locale sous Windows :

- Windows 10 ou 11 avec PowerShell;
- Python 3.12 ou plus récent;
- Docker Desktop avec Docker Compose;
- Node.js `20.19+` ou `22.12+`;
- npm, installé avec Node.js;
- accès au serveur Kafka du GRIDD pour les données réelles;
- identifiants Kafka et certificat CA fournis par le GRIDD.

Git est recommandé, mais il n'est pas nécessaire pour lancer l'application.

### Ports utilisés

| Service | Port | Utilisation |
|---|---:|---|
| Django / Daphne | 8000 | Dashboard, API et WebSockets |
| PostgreSQL | 5433 | Base locale exposée par Docker |
| Redis | 6379 | Diffusion des événements Channels |
| Vite | 5173 | Développement du frontend seulement |

Vérifier que ces ports ne sont pas déjà occupés.

## Installation initiale

Les commandes suivantes sont à exécuter une seule fois après le téléchargement
du projet.

### 1. Démarrer PostgreSQL et Redis

```powershell
cd gridd_django
docker compose up -d
docker compose ps
```

Docker crée des volumes persistants. Les données restent donc disponibles
après un `docker compose stop` ou un redémarrage de l'ordinateur.

### 2. Créer l'environnement Python

Si le dossier `gridd_env` est déjà présent et fonctionnel, cette étape peut être
ignorée.

```powershell
cd gridd_django
python -m venv gridd_env
.\gridd_env\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si PowerShell interdit l'activation du venv, les commandes peuvent être lancées
directement avec :

```powershell
.\gridd_env\Scripts\python.exe manage.py check
```

### 3. Créer le fichier d'environnement

```powershell
Copy-Item .env.example .env
```

Pour utiliser PostgreSQL et Redis fournis par `docker-compose.yml`, placer au
minimum les valeurs suivantes dans `.env` :

```dotenv
DJANGO_SECRET_KEY=remplacer-par-une-cle-locale
DEBUG=true
ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=postgres
DB_NAME=gridd
DB_USER=gridd
DB_PASSWORD=gridd_dev
DB_HOST=localhost
DB_PORT=5433

REDIS_URL=redis://127.0.0.1:6379/0
```

Ne jamais publier `.env`, les identifiants Kafka ou le certificat privé dans un
dépôt Git.

### 4. Configurer Kafka, si nécessaire

Créer le dossier de certificat s'il n'existe pas :

```powershell
New-Item -ItemType Directory -Force .\secrets
```

Placer le certificat CA ici :

```text
gridd_django\secrets\gridd-kafka-ca.crt
```

Puis compléter `.env` :

```dotenv
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=kafka.gridd-dt.ca:9096
KAFKA_USERNAME=nom-utilisateur
KAFKA_PASSWORD=mot-de-passe
KAFKA_CA_CERT_PATH=C:\chemin\vers\gridd_django\secrets\gridd-kafka-ca.crt
KAFKA_GROUP_ID=gridd-django-zone-dashboard-v1
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=SCRAM-SHA-256
```

Les sujets Kafka ont déjà des valeurs par défaut dans `.env.example`.

Pour travailler uniquement avec le simulateur :

```dotenv
KAFKA_ENABLED=false
```

### 5. Installer et compiler React

```powershell
cd frontend
npm.cmd install
npm.cmd run build
```

La compilation produit les fichiers servis par Django dans :

```text
gridd_django\static\dashboard\
```

Il n'est pas nécessaire de laisser un processus Node actif après cette
compilation.

### 6. Préparer Django

```powershell
cd gridd_django
.\gridd_env\Scripts\python.exe manage.py migrate
.\gridd_env\Scripts\python.exe manage.py seed_gridd
.\gridd_env\Scripts\python.exe manage.py check
```

`seed_gridd` crée les zones et capteurs de départ. La commande peut être relancée
si la base est vide.

## Lancement quotidien

Après avoir fermé tous les terminaux ou redémarré l'ordinateur, utiliser trois
terminaux PowerShell.

### Terminal 1 — PostgreSQL et Redis

```powershell
cd gridd_django
docker compose up -d
docker compose ps
```

Les services `postgres` et `redis` doivent être démarrés. Redis est indispensable
aux WebSockets, même si les observations sont correctement enregistrées en base.

### Terminal 2 — Django, API, React et WebSockets

```powershell
cd gridd_django
.\gridd_env\Scripts\python.exe manage.py migrate
.\gridd_env\Scripts\python.exe manage.py runserver
```

Le serveur doit rester actif dans ce terminal.

### Terminal 3 — Événements Kafka

Pour recevoir les données réelles :

```powershell
cd gridd_django
.\gridd_env\Scripts\python.exe manage.py consume_kafka
```

Le terminal doit afficher :

```text
Consumer Kafka démarré.
En attente des données GRIDD...
```

Le consumer doit être redémarré après une modification du code Python; il ne se
recharge pas automatiquement comme le serveur Django de développement.

### Alternative — Simulateur local

Pour tester sans Kafka réel, lancer ceci dans le terminal 3 :

```powershell
cd gridd_django
.\gridd_env\Scripts\python.exe manage.py simulate_gridd --interval 2
```

Éviter de lancer Kafka et le simulateur en même temps, sauf si le mélange de
données réelles et simulées est volontaire.

## Adresses utiles

- Dashboard React : http://127.0.0.1:8000/
- Ancien dashboard Django : http://127.0.0.1:8000/legacy/
- Administration Django : http://127.0.0.1:8000/admin/
- API zones : http://127.0.0.1:8000/api/zones/
- API capteurs : http://127.0.0.1:8000/api/sensors/
- API observations : http://127.0.0.1:8000/api/observations/
- API alertes : http://127.0.0.1:8000/api/alerts/
- État du backend : http://127.0.0.1:8000/api/health/

## Développement du frontend React

Pour modifier React avec rechargement automatique, Django doit déjà fonctionner
sur le port 8000. Ouvrir ensuite un autre terminal :

```powershell
cd frontend
npm.cmd run dev
```

Ouvrir http://127.0.0.1:5173/. Vite redirige `/api` et `/ws` vers Django.

Avant de revenir à la version servie sur le port 8000, recompiler :

```powershell
npm.cmd run typecheck
npm.cmd run build
```

## Vérifications

### Backend

```powershell
cd gridd_django
.\gridd_env\Scripts\python.exe manage.py check
.\gridd_env\Scripts\python.exe manage.py test core
```

### Frontend

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run build
```

### Services Docker

```powershell
cd gridd_django
docker compose ps
```

## Arrêt propre

1. Utiliser `Ctrl+C` dans le terminal Django.
2. Utiliser `Ctrl+C` dans le terminal Kafka ou simulateur.
3. Arrêter PostgreSQL et Redis :

```powershell
cd gridd_django
docker compose stop
```

`docker compose stop` conserve les données. Ne pas utiliser
`docker compose down -v` sauf si la suppression complète de la base locale est
réellement voulue.

## Résolution des problèmes

### Le dashboard indique « Temps réel interrompu »

- vérifier que Django fonctionne sur le port 8000;
- vérifier Redis avec `docker compose ps`;
- vérifier que `REDIS_URL=redis://127.0.0.1:6379/0` est correct;
- actualiser la page après le redémarrage de Redis.

### `InvalidChannelLayerError: Cannot import BACKEND 'channels_redis...'`

Cette erreur signifie que `channels-redis` n'est pas installé dans
l'environnement Python utilisé pour lancer Django. Installer les dépendances
avec l'interpréteur du projet :

```powershell
cd gridd_django
.\gridd_env\Scripts\python.exe -m pip install -r requirements.txt
```

Vérifier ensuite que le paquet est disponible :

```powershell
.\gridd_env\Scripts\python.exe -m pip show channels-redis
```

Arrêter le serveur Django avec `Ctrl+C`, puis le redémarrer :

```powershell
.\gridd_env\Scripts\python.exe manage.py runserver
```

Après un rechargement de la page, le badge « Connexion en cours » doit devenir
« Temps réel actif ».

### Les données sont en base, mais le dashboard ne change pas

- redémarrer `python manage.py consume_kafka` pour charger le code actuel;
- vérifier que le terminal Kafka reçoit encore des messages;
- vérifier que Redis est actif;
- vérifier la console du navigateur pour une erreur WebSocket.

### `KAFKA_ENABLED=false`

Le consumer réel est volontairement désactivé. Modifier `.env` avec
`KAFKA_ENABLED=true`, puis relancer `consume_kafka`.

### Certificat Kafka introuvable

Utiliser un chemin Windows absolu dans `KAFKA_CA_CERT_PATH` et vérifier que le
fichier existe réellement.

### Connexion PostgreSQL refusée

- lancer `docker compose up -d`;
- utiliser le port `5433`, et non le port interne Docker `5432`;
- vérifier que `DB_NAME`, `DB_USER` et `DB_PASSWORD` correspondent au fichier
  `docker-compose.yml`.

### `npm.ps1 cannot be loaded`

PowerShell bloque parfois le script `npm.ps1`. Utiliser `npm.cmd` :

```powershell
npm.cmd install
npm.cmd run build
```

### Le frontend semble ancien après une modification

Recompiler React avec `npm.cmd run build`, puis faire un rechargement forcé du
navigateur avec `Ctrl+F5`.

## Déploiement ASGI

Le projet utilise ASGI, nécessaire aux WebSockets. Le conteneur Django démarre
Daphne avec :

```powershell
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Avant un déploiement, compiler React puis collecter les fichiers statiques :

```powershell
cd frontend
npm.cmd run build

cd ..\gridd_django
.\gridd_env\Scripts\python.exe manage.py collectstatic --noinput
```

Le serveur Django, le consumer Kafka, Redis et PostgreSQL sont quatre processus
distincts en déploiement et doivent tous être supervisés.
