#!/bin/sh
# Point d'entrée du conteneur API.
# - RUN_MIGRATIONS=true : applique les migrations avant de démarrer
#   (à activer sur un seul service pour éviter les exécutions concurrentes).
set -eu

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "[entrypoint] Application des migrations..."
  python manage.py migrate --noinput
fi

exec "$@"
