# Image de l'API GRIDD (Django + Channels, servie par Daphne en ASGI).
# La même image sert aussi au consumer Kafka (commande différente).

ARG PYTHON_VERSION=3.12

# ---------- Dépendances ----------
FROM python:${PYTHON_VERSION}-slim AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install -r requirements.txt

# ---------- Exécution ----------
FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN groupadd --system --gid 10001 gridd \
 && useradd --system --uid 10001 --gid gridd --home-dir /app --shell /usr/sbin/nologin gridd

WORKDIR /app
COPY --from=deps /opt/venv /opt/venv
COPY --chown=gridd:gridd . .

# Les fichiers statiques de l'admin sont collectés à la construction.
# Clé factice : aucun secret n'est intégré à l'image.
RUN DJANGO_SECRET_KEY=collectstatic-only DEBUG=false python manage.py collectstatic --noinput \
 && chown -R gridd:gridd /app/staticfiles

USER gridd
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health/', timeout=3).status == 200 else 1)"

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "--proxy-headers", "config.asgi:application"]
