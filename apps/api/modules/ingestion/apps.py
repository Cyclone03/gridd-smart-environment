from shared.module_config import ModuleConfig


class IngestionConfig(ModuleConfig):
    """Module Ingestion : lit les topics capteurs, valide et qualifie chaque
    mesure, publie les observations validées."""

    name = "modules.ingestion"
    label = "ingestion"
    verbose_name = "GRIDD — ingestion des mesures"

    def subscriptions(self):
        from shared.contracts.topics import Topics
        from shared.messaging import Subscription

        from .consumers.sensor_reading_consumer import SensorReadingConsumer

        return [
            Subscription(
                name="ingestion",
                topics=tuple(Topics.sensors()),
                handler_factory=SensorReadingConsumer.build,
                connection="sensors",
                start_at_live_edge=True,
            )
        ]
