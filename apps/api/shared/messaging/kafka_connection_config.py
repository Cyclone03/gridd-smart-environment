from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class KafkaConnectionConfig:
    """Paramètres de connexion à un cluster Kafka.

    Deux connexions sont définies dans les paramètres (``KAFKA_CONNECTIONS``) :
    ``main`` (bus interne des modules) et ``sensors`` (topics des capteurs).
    Par défaut, ``sensors`` reprend ``main`` ; elle permet de lire les capteurs
    sur le cluster GRIDD tout en publiant les événements internes ailleurs.
    """

    bootstrap_servers: str
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: str = ""
    username: str = ""
    password: str = ""
    ca_cert_path: str = ""

    @classmethod
    def from_settings(cls, name="main") -> "KafkaConnectionConfig":
        try:
            values = settings.KAFKA_CONNECTIONS[name]
        except KeyError as exc:
            raise ImproperlyConfigured(f"Connexion Kafka inconnue : {name}") from exc
        return cls(**values)

    def client_config(self) -> dict:
        """Options communes aux clients confluent-kafka (producteur, consommateur, admin)."""
        if not self.bootstrap_servers:
            raise ImproperlyConfigured("KAFKA_BOOTSTRAP_SERVERS manquant.")
        protocol = self.security_protocol.upper()
        config = {
            "bootstrap.servers": self.bootstrap_servers,
            "security.protocol": protocol,
        }
        if protocol.startswith("SASL"):
            if not self.username or not self.password:
                raise ImproperlyConfigured("KAFKA_USERNAME et KAFKA_PASSWORD sont requis avec SASL.")
            config.update(
                {
                    "sasl.mechanism": self.sasl_mechanism or "SCRAM-SHA-256",
                    "sasl.username": self.username,
                    "sasl.password": self.password,
                }
            )
        if protocol.endswith("SSL"):
            if not self.ca_cert_path:
                raise ImproperlyConfigured("KAFKA_CA_CERT_PATH est requis avec SSL.")
            if not Path(self.ca_cert_path).exists():
                raise ImproperlyConfigured(f"Certificat CA introuvable : {self.ca_cert_path}")
            config.update(
                {
                    "ssl.ca.location": self.ca_cert_path,
                    "enable.ssl.certificate.verification": True,
                }
            )
        return config
