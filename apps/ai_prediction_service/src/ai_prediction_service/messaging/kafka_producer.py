import logging
import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from confluent_kafka import KafkaException, Producer

from .prediction_event import ClimatePredictionEvent
from .weather_snapshot_event import WeatherSnapshotEvent
from ..domain.weather import WeatherSnapshot

logger = logging.getLogger(__name__)

DEFAULT_PREDICTIONS_TOPIC = "gridd.backend.ai_prediction.events"
PRODUCER_CLIENT_ID = "gridd-ai-prediction-service"


class PredictionPublicationError(RuntimeError):
    """Kafka did not acknowledge a climate prediction event."""


@dataclass(frozen=True)
class KafkaDeliveryReceipt:
    event_id: str
    topic: str
    zone_code: str | None
    partition: int
    offset: int


@dataclass(frozen=True)
class KafkaProducerConfig:
    bootstrap_servers: str
    topic: str = DEFAULT_PREDICTIONS_TOPIC
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: str = "SCRAM-SHA-256"
    username: str = ""
    password: str = ""
    ca_cert_path: str = ""
    publish_timeout_seconds: float = 10.0
    client_id: str = PRODUCER_CLIENT_ID

    def __post_init__(self):
        if not self.bootstrap_servers.strip():
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS is required.")
        if not self.topic.strip():
            raise ValueError("KAFKA_TOPIC_AI_PREDICTIONS must not be empty.")

        protocol = self.security_protocol.strip().upper()
        if protocol not in {"PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"}:
            raise ValueError(f"Unsupported Kafka security protocol: {protocol!r}.")
        object.__setattr__(self, "security_protocol", protocol)

        if protocol.startswith("SASL") and (
            not self.username.strip() or not self.password.strip()
        ):
            raise ValueError("KAFKA_USERNAME and KAFKA_PASSWORD are required with SASL.")
        if protocol.startswith("SASL") and not self.sasl_mechanism.strip():
            object.__setattr__(self, "sasl_mechanism", "SCRAM-SHA-256")
        if protocol.endswith("SSL"):
            if not self.ca_cert_path:
                raise ValueError("KAFKA_CA_CERT_PATH is required with SSL.")
            if not Path(self.ca_cert_path).exists():
                raise ValueError(f"Kafka CA certificate not found: {self.ca_cert_path}")

        if (
            isinstance(self.publish_timeout_seconds, bool)
            or not math.isfinite(self.publish_timeout_seconds)
            or self.publish_timeout_seconds <= 0
        ):
            raise ValueError("KAFKA_PUBLISH_TIMEOUT_SECONDS must be greater than zero.")
        if not self.client_id.strip():
            raise ValueError("Kafka client id must not be empty.")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "KafkaProducerConfig":
        values = os.environ if environ is None else environ
        try:
            timeout = float(values.get("KAFKA_PUBLISH_TIMEOUT_SECONDS", "10"))
        except (TypeError, ValueError) as exc:
            raise ValueError("KAFKA_PUBLISH_TIMEOUT_SECONDS must be a number.") from exc

        return cls(
            bootstrap_servers=values.get("KAFKA_BOOTSTRAP_SERVERS", "").strip(),
            topic=values.get("KAFKA_TOPIC_AI_PREDICTIONS", DEFAULT_PREDICTIONS_TOPIC).strip(),
            security_protocol=values.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
            sasl_mechanism=(values.get("KAFKA_SASL_MECHANISM") or "SCRAM-SHA-256").strip(),
            username=values.get("KAFKA_USERNAME", "").strip(),
            password=values.get("KAFKA_PASSWORD", ""),
            ca_cert_path=values.get("KAFKA_CA_CERT_PATH", "").strip(),
            publish_timeout_seconds=timeout,
        )

    def describe(self) -> str:
        """Connection summary for logs; never includes the password."""
        parts = [
            f"bootstrap={self.bootstrap_servers}",
            f"security.protocol={self.security_protocol}",
            f"topic={self.topic}",
        ]
        if self.security_protocol.startswith("SASL"):
            parts.append(f"sasl.mechanism={self.sasl_mechanism}")
            parts.append(f"sasl.username={self.username}")
        if self.security_protocol.endswith("SSL"):
            parts.append(f"ssl.ca.location={self.ca_cert_path}")
        return " ".join(parts)

    def client_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": self.client_id,
            "security.protocol": self.security_protocol,
            "acks": "all",
            "enable.idempotence": True,
        }
        if self.security_protocol.startswith("SASL"):
            config.update(
                {
                    "sasl.mechanism": self.sasl_mechanism,
                    "sasl.username": self.username,
                    "sasl.password": self.password,
                }
            )
        if self.security_protocol.endswith("SSL"):
            config.update(
                {
                    "ssl.ca.location": self.ca_cert_path,
                    "enable.ssl.certificate.verification": True,
                }
            )
        return config


class KafkaPredictionProducer:
    """Publishes predictions using the backend's JSON event envelope."""

    BUFFER_FULL_WAIT_SECONDS = 1.0

    def __init__(self, config: KafkaProducerConfig, producer: Producer | None = None):
        self._config = config
        self._producer = producer if producer is not None else Producer(config.client_config())
        logger.info("Kafka producer configured: %s", config.describe())

    @classmethod
    def from_env(
        cls, environ: Mapping[str, str] | None = None
    ) -> "KafkaPredictionProducer":
        return cls(KafkaProducerConfig.from_env(environ))

    def publish_prediction(
        self,
        *,
        zone_code: str,
        target_at: datetime,
        predicted_temperature_c: float,
        predicted_humidity_percent: float,
        model_version: str,
        prediction_mode: str,
        event_id: str | None = None,
        generated_at: datetime | None = None,
    ) -> KafkaDeliveryReceipt:
        event = ClimatePredictionEvent.create(
            zone_code=zone_code,
            target_at=target_at,
            predicted_temperature_c=predicted_temperature_c,
            predicted_humidity_percent=predicted_humidity_percent,
            model_version=model_version,
            prediction_mode=prediction_mode,
            event_id=event_id,
            generated_at=generated_at,
        )
        try:
            receipt = self._publish(event, key=zone_code, zone_code=zone_code)
        except PredictionPublicationError as exc:
            logger.error(
                "Kafka publication failed for prediction event %s (zone=%s): %s",
                event.event_id,
                zone_code,
                exc,
            )
            raise

        logger.info(
            "Climate prediction published: event_id=%s zone=%s target_at=%s "
            "topic=%s partition=%s offset=%s",
            receipt.event_id,
            receipt.zone_code,
            event.target_at,
            receipt.topic,
            receipt.partition,
            receipt.offset,
        )
        return receipt

    def publish_weather_snapshot(
        self,
        snapshot: WeatherSnapshot,
        *,
        generated_at: datetime | None = None,
    ) -> KafkaDeliveryReceipt:
        event = WeatherSnapshotEvent.create(snapshot=snapshot, generated_at=generated_at)
        try:
            receipt = self._publish(event, key="weather", zone_code=None)
        except PredictionPublicationError as exc:
            logger.error(
                "Kafka publication failed for weather snapshot %s: %s",
                event.event_id,
                exc,
            )
            raise

        logger.info(
            "Weather snapshot published: event_id=%s generated_at=%s current_at=%s "
            "forecast_h1_at=%s topic=%s partition=%s offset=%s",
            receipt.event_id,
            event.generated_at,
            event.current_at,
            event.forecast_h1_at,
            receipt.topic,
            receipt.partition,
            receipt.offset,
        )
        return receipt

    def _publish(
        self,
        event: ClimatePredictionEvent | WeatherSnapshotEvent,
        *,
        key: str,
        zone_code: str | None,
    ) -> KafkaDeliveryReceipt:
        delivery_reports = []

        def on_delivery(error, message):
            delivery_reports.append((error, message))

        def produce():
            self._producer.produce(
                self._config.topic,
                value=event.encode(),
                key=key,
                on_delivery=on_delivery,
            )

        try:
            try:
                produce()
            except BufferError:
                self._producer.poll(self.BUFFER_FULL_WAIT_SECONDS)
                try:
                    produce()
                except BufferError as exc:
                    raise PredictionPublicationError(
                        f"Kafka producer queue remained full for {self._config.topic}."
                    ) from exc
        except KafkaException as exc:
            raise PredictionPublicationError(
                f"Kafka rejected event for {self._config.topic}."
            ) from exc

        try:
            outstanding = self._producer.flush(self._config.publish_timeout_seconds)
        except KafkaException as exc:
            raise PredictionPublicationError(
                f"Kafka flush failed for {self._config.topic}."
            ) from exc
        if outstanding:
            hint = ""
            if self._config.security_protocol == "PLAINTEXT":
                hint = (
                    " If librdkafka logs 'Disconnected ... in state APIVERSION_QUERY', the broker "
                    "listener expects TLS/SASL: check KAFKA_BOOTSTRAP_SERVERS and "
                    "KAFKA_SECURITY_PROTOCOL."
                )
            raise PredictionPublicationError(
                f"Kafka delivery timed out for {self._config.topic} "
                f"({outstanding} message(s) outstanding; {self._config.describe()}).{hint}"
            )
        if not delivery_reports:
            raise PredictionPublicationError(
                f"Kafka returned no delivery report for event {event.event_id}."
            )

        error, message = delivery_reports[0]
        if error is not None:
            raise PredictionPublicationError(
                f"Kafka delivery failed for event {event.event_id}: {error}"
            )
        if message is None:
            raise PredictionPublicationError(
                f"Kafka acknowledged event {event.event_id} without message metadata."
            )
        return KafkaDeliveryReceipt(
            event_id=event.event_id,
            topic=message.topic(),
            zone_code=zone_code,
            partition=message.partition(),
            offset=message.offset(),
        )
