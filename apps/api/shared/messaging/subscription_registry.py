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
        subscriptions = self.all()
        if not names:
            return subscriptions
        known = {subscription.name for subscription in subscriptions}
        unknown = sorted(set(names) - known)
        if unknown:
            raise ValueError(f"Module(s) sans abonnement : {', '.join(unknown)}. Disponibles : {', '.join(sorted(known))}.")
        return [subscription for subscription in subscriptions if subscription.name in names]
