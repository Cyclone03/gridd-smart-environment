import logging
import signal
import subprocess
import sys
import threading
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger("modules.ia")


class Command(BaseCommand):
    help = (
        "Planificateur des prédictions IA : un cycle immédiatement puis toutes les "
        "AI_PREDICTION_INTERVAL_SECONDS. --once exécute un seul cycle."
    )

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Un seul cycle, dans ce processus.")
        parser.add_argument("--zone", help="Avec --once : une seule zone (code GRIDD).")

    def handle(self, *args, **options):
        from modules.ia import composition

        if options["once"]:
            try:
                exit_code = composition.prediction_cycle().run(zone_code=options["zone"])
            except Exception:
                logger.exception("Prediction cycle failed.")
                exit_code = 1
            if exit_code:
                sys.exit(exit_code)
            return

        stop_event = threading.Event()

        def request_stop(signum, _frame):
            logger.info("Received signal %s; stopping after the current prediction cycle.", signum)
            stop_event.set()

        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)
        scheduler_settings = composition.scheduler_settings()
        logger.info(
            "Starting prediction scheduler: interval_seconds=%s heartbeat=%s",
            scheduler_settings.interval_seconds,
            scheduler_settings.heartbeat_path,
        )
        composition.prediction_scheduler(self._run_cycle_in_subprocess).run(stop_event)

    @staticmethod
    def _run_cycle_in_subprocess() -> int:
        # Chaque cycle dans un processus neuf : la mémoire de TensorFlow est
        # rendue au système et une erreur fatale n'arrête pas le planificateur.
        manage = Path(settings.BASE_DIR) / "manage.py"
        return subprocess.run([sys.executable, str(manage), "run_ai_predictions", "--once"], check=False).returncode
