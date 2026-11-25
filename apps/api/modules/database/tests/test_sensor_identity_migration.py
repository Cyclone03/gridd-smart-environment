from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class SensorPerZoneMigrationTests(TransactionTestCase):
    """0018 : les capteurs par nœud GRIDD deviennent un capteur par zone et par mesure."""

    before = [("core", "0017_weather_snapshot")]
    after = [("core", "0018_sensor_per_zone_and_metric")]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        self.old_apps = executor.loader.project_state(self.before).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def migrate_forward(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.after)
        return executor.loader.project_state(self.after).apps

    def test_observations_move_to_the_sensor_of_their_own_zone(self):
        Zone = self.old_apps.get_model("core", "Zone")
        Sensor = self.old_apps.get_model("core", "Sensor")
        Observation = self.old_apps.get_model("core", "Observation")
        cubicle_01 = Zone.objects.create(name="Cubicule 01", code="individual-work-cubicle-01")
        cubicle_02 = Zone.objects.create(name="Cubicule 02", code="individual-work-cubicle-02")
        # Capteur de démonstration désactivé par seed_gridd (un capteur réel existait).
        Sensor.objects.create(
            node_id="individual-work-cubicle-02-temperature", sensor_type="temperature",
            zone=cubicle_02, unit="°C", active=False,
        )
        # node03 : enregistré au cubicule 01, puis déplacé au cubicule 02.
        node03 = Sensor.objects.create(node_id="environmental-node03", sensor_type="temperature", zone=cubicle_02, unit="C")
        now = timezone.now()
        Observation.objects.create(sensor=node03, zone=cubicle_01, type="temperature", value=20, unit="C", observed_at=now)
        Observation.objects.create(sensor=node03, zone=cubicle_02, type="temperature", value=21, unit="C", observed_at=now)

        apps = self.migrate_forward()

        Sensor = apps.get_model("core", "Sensor")
        Observation = apps.get_model("core", "Observation")
        self.assertFalse(Sensor.objects.filter(node_id="environmental-node03").exists())
        by_zone = {
            obs.zone_id: Sensor.objects.get(pk=obs.sensor_id)
            for obs in Observation.objects.all()
        }
        self.assertEqual(by_zone[cubicle_01.pk].node_id, "individual-work-cubicle-01-temperature")
        self.assertEqual(by_zone[cubicle_02.pk].node_id, "individual-work-cubicle-02-temperature")
        self.assertTrue(by_zone[cubicle_02.pk].active)
        self.assertEqual(by_zone[cubicle_01.pk].metadata["source_node_id"], "environmental-node03")
        self.assertEqual(Sensor.objects.count(), 2)
