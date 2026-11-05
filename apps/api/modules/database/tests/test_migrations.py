from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ThresholdConversionMigrationTests(TransactionTestCase):
    """Vérifie la conversion des anciens seuils fixes en règles d'alarme."""

    before = [("core", "0011_alarm_rules")]
    after = [("core", "0013_remove_profile_thresholds")]

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

    def make_zone(self, code, **profile):
        Zone = self.old_apps.get_model("core", "Zone")
        ThresholdProfile = self.old_apps.get_model("core", "ThresholdProfile")
        zone = Zone.objects.create(name=code, code=code)
        ThresholdProfile.objects.create(zone=zone, **profile)
        return zone

    def test_identical_profiles_become_global_rules(self):
        self.make_zone("a", enabled=False)
        self.make_zone("b", enabled=False)
        Alert = self.old_apps.get_model("core", "Alert")
        Alert.objects.create(
            zone_id=self.old_apps.get_model("core", "Zone").objects.get(code="a").id,
            code="TEMPERATURE_OUT_OF_RANGE",
            message="ancienne",
            severity="warning",
        )

        apps = self.migrate_forward()
        rules = apps.get_model("core", "AlarmRule").objects.order_by("id")
        self.assertEqual(
            [(r.metric, r.operator, r.threshold, r.threshold_high, r.zone_id, r.enabled) for r in rules],
            [
                ("temperature", "outside_range", 15, 30, None, False),
                ("humidity", "outside_range", 30, 60, None, False),
                ("sound_level", "gte", 50, None, None, False),
                ("sound_level", "gt", 80, None, None, False),
            ],
        )
        legacy = apps.get_model("core", "Alert").objects.get(code="TEMPERATURE_OUT_OF_RANGE")
        self.assertEqual((legacy.active, legacy.resolution), (False, "migrated"))

    def test_different_profiles_become_zone_rules(self):
        self.make_zone("a", enabled=True, temperature_min=18, temperature_max=26)
        self.make_zone("b", enabled=False)

        apps = self.migrate_forward()
        AlarmRule = apps.get_model("core", "AlarmRule")
        self.assertEqual(AlarmRule.objects.count(), 8)
        rule = AlarmRule.objects.get(zone__code="a", metric="temperature")
        self.assertEqual((rule.threshold, rule.threshold_high, rule.enabled), (18, 26, True))
        self.assertFalse(AlarmRule.objects.get(zone__code="b", metric="temperature").enabled)
