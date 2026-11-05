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

        # Les commandes ont leur propre consommateur : une réponse attendue par
        # l'API ne doit jamais patienter derrière un arriéré de mesures.
        topics = Topics.database_subscriptions()
        commands = tuple(topic for topic in topics if topic in Topics.commands())
        events = tuple(topic for topic in topics if topic not in commands)
        return [
            Subscription(name=name, topics=group, handler_factory=PersistenceConsumer.build)
            for name, group in (("database", events), ("database-commands", commands))
            if group
        ]
