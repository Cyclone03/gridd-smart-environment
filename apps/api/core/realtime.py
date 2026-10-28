"""Diffusion temps réel vers les tableaux de bord (Django Channels).

Une panne du channel layer (Redis indisponible) ne doit jamais annuler
l'ingestion d'une mesure : les erreurs sont journalisées puis ignorées.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction


logger = logging.getLogger(__name__)

DASHBOARD_GROUP = "dashboard"


def zone_group(zone_code):
    return f"zone_{zone_code}"


def _send(groups, event):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning("Aucun channel layer configuré : événement %s non diffusé.", event["type"])
        return
    try:
        for group in groups:
            async_to_sync(channel_layer.group_send)(group, event)
    except Exception:
        # La donnée est déjà enregistrée. Une panne WebSocket ne doit pas
        # faire rejouer le message Kafka et créer un doublon en base.
        logger.exception("Impossible de diffuser l'événement %s.", event["type"])


def observation_payload(observation):
    return {
        "id": observation.pk,
        "zone": observation.zone_id,
        "zone_code": observation.zone.code,
        "zone_name": observation.zone.name,
        "sensor": observation.sensor_id,
        "sensor_node_id": observation.sensor.node_id,
        "type": observation.type,
        "value": observation.value,
        "unit": observation.unit,
        "observed_at": observation.observed_at.isoformat() if observation.observed_at else None,
        "received_at": observation.received_at.isoformat(),
        "quality_status": observation.quality_status,
        "quality_reason": observation.quality_reason,
        "metadata": observation.metadata,
    }


def broadcast_observation(payload):
    _send(
        [DASHBOARD_GROUP, zone_group(payload["zone_code"])],
        {"type": "observation.created", "payload": payload},
    )


def broadcast_alerts_changed():
    _send([DASHBOARD_GROUP], {"type": "alerts.changed"})


def schedule_alerts_changed():
    """Notifie les tableaux de bord après validation de la transaction."""
    transaction.on_commit(broadcast_alerts_changed)
