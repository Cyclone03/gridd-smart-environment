# Images GRIDD construites depuis le même code (apps/api) :
#   --target api : Django + Channels + Daphne + Kafka (image légère, par défaut)
#   --target ia  : même code + TensorFlow / scikit-learn pour le module IA
ARG PYTHON_VERSION=3.12

# ---------- Dépendances de l'API ----------
FROM python:${PYTHON_VERSION}-slim AS deps

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt


# ---------- Dépendances de l'IA (en plus de celles de l'API) ----------
FROM deps AS deps-ia

COPY requirements-ia.txt .

RUN /opt/venv/bin/pip install -r requirements-ia.txt


# ---------- Base d'exécution commune ----------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings

RUN groupadd --system --gid 10001 gridd \
    && useradd --system --uid 10001 --gid gridd \
       --home-dir /app --shell /usr/sbin/nologin gridd

WORKDIR /app


# ---------- Image IA : planificateur des prédictions ----------
FROM runtime AS ia

COPY --from=deps-ia /opt/venv /opt/venv

COPY --chown=gridd:gridd . .

# État persistant (registre des publications, battement de cœur) : volume.
ENV AI_STATE_DIR=/var/lib/ai-predictions \
    AI_PREDICTION_LEDGER_PATH=/var/lib/ai-predictions/predictions.sqlite3 \
    AI_PREDICTION_HEARTBEAT_PATH=/var/lib/ai-predictions/heartbeat \
    AI_ARTIFACT_MANIFEST_PATH=/app/modules/ia/artifacts/manifest.json \
    AI_ISOLATED_ENVIRONMENT=true

RUN mkdir -p /var/lib/ai-predictions \
    && chown -R gridd:gridd /var/lib/ai-predictions

USER gridd

VOLUME ["/var/lib/ai-predictions"]

HEALTHCHECK --interval=60s \
    --timeout=20s \
    --start-period=300s \
    --retries=3 \
    CMD ["python", "manage.py", "ai_prediction_healthcheck"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]

CMD ["python", "manage.py", "run_ai_predictions"]


# ---------- Image API (cible par défaut : dernière étape) ----------
FROM runtime AS api

COPY --from=deps /opt/venv /opt/venv

COPY --chown=gridd:gridd . .

# Collecte des fichiers statiques
RUN DJANGO_SECRET_KEY=collectstatic-only \
    DEBUG=false \
    python manage.py collectstatic --noinput \
    && mkdir -p /app/staticfiles \
    && chown -R gridd:gridd /app/staticfiles

USER gridd

EXPOSE 8000

HEALTHCHECK --interval=30s \
    --timeout=5s \
    --start-period=40s \
    --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health/', timeout=3).status == 200 else 1)"

ENTRYPOINT ["/app/docker/entrypoint.sh"]

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "--proxy-headers", "config.asgi:application"]
