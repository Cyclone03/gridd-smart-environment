from shared.module_config import ModuleConfig


class DatabaseConfig(ModuleConfig):
    """Module Database : seul module autorisé à écrire en base.

    Le label ``core`` conserve les noms de tables et l'historique des
    migrations existants.
    """

    name = "modules.database"
    label = "core"
    verbose_name = "GRIDD — base de données"

    def subscriptions(self):
        from shared.contracts.topics import Topics
        from shared.messaging import Subscription

        from .consumers.persistence_consumer import PersistenceConsumer

        return [
            Subscription(
                name="database",
                topics=Topics.database_subscriptions(),
                handler_factory=PersistenceConsumer.build,
            )
        ]
