from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Contrôle de santé du conteneur IA : le battement du planificateur doit être récent."

    def handle(self, *args, **options):
        from modules.ia import composition

        settings = composition.scheduler_settings()
        if not composition.heartbeat().is_fresh(settings.heartbeat_max_age_seconds):
            raise CommandError("Prediction scheduler heartbeat is missing or stale.")
