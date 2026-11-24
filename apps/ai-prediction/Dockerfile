FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AI_ARTIFACT_MANIFEST_PATH=/app/artifacts/manifest.json

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/
COPY artifacts/ ./artifacts/

RUN python -m pip install --no-cache-dir '.[inference]'

RUN groupadd --system --gid 10001 ai-prediction \
    && mkdir -p /home/ai-prediction /var/lib/ai-predictions \
    && useradd --system --uid 10001 --gid ai-prediction --home-dir /home/ai-prediction ai-prediction \
    && chown -R ai-prediction:ai-prediction /var/lib/ai-predictions /home/ai-prediction

ENV AI_PREDICTION_LEDGER_PATH=/var/lib/ai-predictions/predictions.sqlite3 \
    AI_PREDICTION_HEARTBEAT_PATH=/var/lib/ai-predictions/heartbeat

USER ai-prediction
VOLUME ["/var/lib/ai-predictions"]

HEALTHCHECK --interval=60s --timeout=5s --start-period=300s --retries=3 \
    CMD ["python", "-m", "ai_prediction_service.healthcheck"]

CMD ["python", "-m", "ai_prediction_service.scheduler"]
