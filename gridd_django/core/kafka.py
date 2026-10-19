import json
import os
from pathlib import Path

from confluent_kafka import Consumer
from django.utils.dateparse import parse_datetime

from .services import ingest_observation


TOPIC_TO_TYPE = {
    os.getenv(
        "KAFKA_TOPIC_TEMPERATURE",
        "gridd.obs.environmental.temperature",
    ): "temperature",

    os.getenv(
        "KAFKA_TOPIC_HUMIDITY",
        "gridd.obs.environmental.humidity",
    ): "humidity",

    os.getenv(
        "KAFKA_TOPIC_CO2",
        "gridd.obs.environmental.co2",
    ): "co2",

    os.getenv(
        "KAFKA_TOPIC_SOUND",
        "gridd.obs.acoustic.sound_level",
    ): "sound_level",

    os.getenv(
        "KAFKA_TOPIC_OCCUPANCY",
        "gridd.obs.occupancy.count",
    ): "occupancy",
}


def build_consumer():
    """
    Construit le consumer Kafka GRIDD avec :
    - TLS
    - certificat CA
    - SASL SCRAM-SHA-256
    """

    ca_path = os.getenv(
        "KAFKA_CA_CERT_PATH",
        "",
    )

    if not ca_path:
        raise RuntimeError(
            "KAFKA_CA_CERT_PATH manquant"
        )

    if not Path(ca_path).exists():
        raise RuntimeError(
            "Certificat CA introuvable: "
            f"{ca_path}"
        )

    username = os.getenv(
        "KAFKA_USERNAME",
        "",
    )

    password = os.getenv(
        "KAFKA_PASSWORD",
        "",
    )

    if not username:
        raise RuntimeError(
            "KAFKA_USERNAME manquant"
        )

    if not password:
        raise RuntimeError(
            "KAFKA_PASSWORD manquant"
        )

    bootstrap_servers = os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS",
        "kafka.gridd-dt.ca:9096",
    )

    group_id = os.getenv(
        "KAFKA_GROUP_ID",
        "gridd-django-dashboard",
    )

    sasl_mechanism = os.getenv(
        "KAFKA_SASL_MECHANISM",
        "SCRAM-SHA-256",
    )

    return Consumer(
        {
            "bootstrap.servers":
                bootstrap_servers,

            "group.id":
                group_id,

            "auto.offset.reset":
                "latest",

            "enable.auto.commit":
                False,

            "security.protocol":
                "SASL_SSL",

            "sasl.mechanism":
                sasl_mechanism,

            "sasl.username":
                username,

            "sasl.password":
                password,

            "ssl.ca.location":
                ca_path,

            "enable.ssl.certificate.verification":
                True,
        }
    )


def process_message(
    topic,
    raw_value,
):
    """
    Transforme un message Kafka en Observation Django.
    """

    try:
        payload = json.loads(
            raw_value.decode(
                "utf-8",
            )
        )

    except Exception as exc:
        raise ValueError(
            "JSON Kafka invalide"
        ) from exc

    if topic not in TOPIC_TO_TYPE:
        raise ValueError(
            f"topic inconnu: {topic}"
        )

    expected_type = (
        TOPIC_TO_TYPE[topic]
    )

    message_type = payload.get(
        "type",
        expected_type,
    )

    if message_type != expected_type:
        raise ValueError(
            "type/topic incohérent: "
            f"type={message_type}, "
            f"topic={topic}"
        )

    node_id = (
        payload.get(
            "node_id"
        )
        or payload.get(
            "nodeId"
        )
    )

    if not node_id:
        raise ValueError(
            "node_id manquant "
            f"sur topic={topic}"
        )

    if "value" not in payload:
        raise ValueError(
            f"value manquante: {node_id}"
        )

    if "unit" not in payload:
        raise ValueError(
            f"unit manquante: {node_id}"
        )

    observed_raw = (
        payload.get(
            "timestamp"
        )
        or payload.get(
            "observed_at"
        )
        or payload.get(
            "observedAt"
        )
    )

    observed_at = None

    if observed_raw:
        observed_at = (
            parse_datetime(
                observed_raw,
            )
        )

        if observed_at is None:
            raise ValueError(
                "timestamp invalide: "
                f"{observed_raw}"
            )

    metadata = payload.get(
        "metadata",
        {},
    )

    if not isinstance(
        metadata,
        dict,
    ):
        raise ValueError(
            "metadata doit être un objet JSON"
        )

    try:
        observation = (
            ingest_observation(
                node_id=node_id,
                observation_type=
                    message_type,
                value=payload[
                    "value"
                ],
                unit=payload[
                    "unit"
                ],
                observed_at=
                    observed_at,
                metadata=metadata,
            )
        )

        return observation

    except Exception as exc:
        zone_metadata = (
            metadata.get(
                "zone",
                {},
            )
        )

        zone_id = (
            zone_metadata.get(
                "id",
                "unknown",
            )
        )

        raise ValueError(
            f"topic={topic} "
            f"node_id={node_id} "
            f"zone={zone_id} "
            f"type={message_type} "
            f"value={payload.get('value')} "
            f"unit={payload.get('unit')} "
            f"error={exc}"
        ) from exc