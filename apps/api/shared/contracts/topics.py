from django.conf import settings


class Topics:
    """Noms des topics Kafka, tous configurables par variables d'environnement.

    - topics capteurs (entrée du système, alimentés par les capteurs GRIDD) ;
    - un ou deux topics de sortie par module : chaque module publie dans ses
      propres topics et ne lit que ceux qui le concernent.

    Les valeurs sont lues à chaque appel pour rester compatibles avec
    ``override_settings`` dans les tests.
    """

    @staticmethod
    def sensors() -> dict[str, str]:
        """Topics capteurs : nom du topic → type de mesure."""
        return dict(settings.KAFKA_SENSOR_TOPICS)

    @classmethod
    def sensor_topic_for(cls, metric) -> str | None:
        for topic, topic_metric in cls.sensors().items():
            if topic_metric == metric:
                return topic
        return None

    @staticmethod
    def ingestion_observations() -> str:
        return settings.KAFKA_TOPICS["ingestion_observations"]

    @staticmethod
    def alarms_events() -> str:
        return settings.KAFKA_TOPICS["alarms_events"]

    @staticmethod
    def alarms_commands() -> str:
        return settings.KAFKA_TOPICS["alarms_commands"]

    @staticmethod
    def comfort_events() -> str:
        return settings.KAFKA_TOPICS["comfort_events"]

    @staticmethod
    def comfort_commands() -> str:
        return settings.KAFKA_TOPICS["comfort_commands"]

    @staticmethod
    def energy_events() -> str:
        return settings.KAFKA_TOPICS["energy_events"]

    @staticmethod
    def energy_commands() -> str:
        return settings.KAFKA_TOPICS["energy_commands"]

    @staticmethod
    def database_events() -> str:
        return settings.KAFKA_TOPICS["database_events"]

    @staticmethod
    def database_replies() -> str:
        return settings.KAFKA_TOPICS["database_replies"]

    @staticmethod
    def database_subscriptions() -> tuple[str, ...]:
        """Topics que le module Database persiste (DATABASE_SUBSCRIBED_TOPICS)."""
        return tuple(settings.DATABASE_SUBSCRIBED_TOPICS)

    @classmethod
    def commands(cls) -> tuple[str, ...]:
        """Topics de commandes (requête-réponse avec l'API)."""
        return (cls.alarms_commands(), cls.comfort_commands(), cls.energy_commands())

    @staticmethod
    def internal() -> tuple[str, ...]:
        """Topics produits par le backend lui-même."""
        return tuple(dict.fromkeys(settings.KAFKA_TOPICS.values()))
