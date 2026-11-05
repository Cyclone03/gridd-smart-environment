from django.apps import apps

from shared.module_config import ModuleConfig


class SubscriptionRegistry:
    """Collecte les abonnements déclarés par les modules installés."""

    def all(self):
        subscriptions = []
        for config in apps.get_app_configs():
            if isinstance(config, ModuleConfig):
                subscriptions.extend(config.subscriptions())
        return subscriptions

    def select(self, names=None):
        """Abonnements à démarrer. Un nom de module inclut ses abonnements
        secondaires : ``database`` sélectionne aussi ``database-commands``."""
        subscriptions = self.all()
        if not names:
            return subscriptions
        known = {subscription.name for subscription in subscriptions}
        known |= {self._module_of(name) for name in known}
        unknown = sorted(set(names) - known)
        if unknown:
            available = ", ".join(sorted(known))
            raise ValueError(f"Module(s) sans abonnement : {', '.join(unknown)}. Disponibles : {available}.")
        return [item for item in subscriptions if item.name in names or self._module_of(item.name) in names]

    @staticmethod
    def _module_of(subscription_name):
        return subscription_name.split("-", 1)[0]
