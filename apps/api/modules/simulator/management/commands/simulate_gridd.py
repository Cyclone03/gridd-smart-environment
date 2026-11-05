import time

from django.core.management.base import BaseCommand

from modules.simulator.services.simulator_service import SimulatorService


class Command(BaseCommand):
    help = "Publie des mesures simulées sur les topics capteurs, pour chaque capteur actif."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=30.0, help="Secondes entre deux séries de mesures")
        parser.add_argument("--iterations", type=int, default=0, help="Nombre de séries (0 = sans fin)")

    def handle(self, *args, **options):
        simulator = SimulatorService.build()
        count = simulator.start()
        self.stdout.write(f"Simulateur GRIDD démarré ({count} capteurs). Ctrl+C pour arrêter.")
        iteration = 0
        try:
            while not options["iterations"] or iteration < options["iterations"]:
                simulator.tick()
                iteration += 1
                if not options["iterations"] or iteration < options["iterations"]:
                    time.sleep(options["interval"])
        except KeyboardInterrupt:
            self.stdout.write("")
        self.stdout.write("Simulateur arrêté.")
