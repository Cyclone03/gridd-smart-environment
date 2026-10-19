# GRIDD Smart Environment

Tableau de bord de supervision environnementale du GRIDD. Le backend Django
enregistre les observations dans PostgreSQL et les diffuse au frontend React en
temps réel avec Django Channels, Redis et WebSocket.

## Prérequis

- Windows 10 ou 11 avec PowerShell;
- Python 3.12 ou 3.13;
- Docker Desktop avec Docker Compose;
- Node.js 20.19+ ou 22.12+;
- npm.

Kafka et son certificat ne sont nécessaires que pour recevoir les données
réelles. Le simulateur inclus permet de tester tout le projet localement.

## Installation rapide

Depuis la racine du dépôt :

```powershell
cd gridd_django
Copy-Item .env.example .env
docker compose up -d

py -m venv gridd_env
.\gridd_env\Scripts\python.exe -m pip install --upgrade pip
.\gridd_env\Scripts\python.exe -m pip install -r requirements.txt

cd ..\frontend
npm.cmd ci
npm.cmd run build

cd ..\gridd_django
.\gridd_env\Scripts\python.exe manage.py migrate
.\gridd_env\Scripts\python.exe manage.py seed_gridd
.\gridd_env\Scripts\python.exe manage.py check
```

## Démarrage

Après l'installation, ouvrir deux terminaux PowerShell.

Terminal 1 — services et serveur :

```powershell
cd gridd_django
docker compose up -d
.\gridd_env\Scripts\python.exe manage.py runserver
```

Terminal 2 — données simulées :

```powershell
cd gridd_django
.\gridd_env\Scripts\python.exe manage.py simulate_gridd --interval 2
```

Ouvrir ensuite <http://127.0.0.1:8000/>. Le badge « Temps réel actif » confirme
que le WebSocket fonctionne.

Pour utiliser Kafka, la configuration détaillée, les tests et le dépannage,
consulter la [documentation complète](gridd_django/README.md).

## Données sensibles

Ne jamais versionner `.env`, `secrets/`, un certificat privé ni des identifiants
Kafka. Ces chemins sont exclus par `.gitignore`. Seul `.env.example`, sans secret,
doit être publié.

## Structure

```text
.
├── frontend/       # React, TypeScript et Vite
└── gridd_django/   # Django, Channels, Kafka, PostgreSQL et Redis
```
