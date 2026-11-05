from django.apps import AppConfig


class ModuleConfig(AppConfig):
    """Configuration commune des modules GRIDD.

    Chaque module déclare ici les abonnements Kafka qu'il assure.
    ``SubscriptionRegistry`` les collecte sans que les modules aient à se
    connaître : ajouter un module consiste à l'inscrire dans ``INSTALLED_APPS``.
    """

    default_auto_field = "django.db.models.BigAutoField"

    def subscriptions(self):
        """Abonnements du module (liste de ``shared.messaging.Subscription``)."""
        return []
