from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from .permissions import ensure_alarm_managers_group

        post_migrate.connect(ensure_alarm_managers_group, sender=self)
