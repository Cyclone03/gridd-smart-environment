from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from modules.database.models import AlarmRule, AlarmRuleState, Alert, Sensor, ThresholdProfile, Zone
from shared.contracts.event_types import EventTypes
from shared.contracts.topics import Topics
from shared.messaging import Event, Messaging
from tests.support.sensor_pipeline import SensorPipeline

Status = AlarmRuleState.Status


class AlarmPipelineTests(TestCase):
    """Évaluation réelle : mesure capteur → ingestion → database → alarms → database."""

    def setUp(self):
        self.zone = Zone.objects.create(name="Salle de réunion", code="meeting-room")
        self.other_zone = Zone.objects.create(name="Bureau", code="office")
        # Profils désactivés : pas d'alerte de variation rapide parasite.
        ThresholdProfile.objects.create(zone=self.zone, enabled=False)
        ThresholdProfile.objects.create(zone=self.other_zone, enabled=False)
        Sensor.objects.create(node_id="sound-1", sensor_type="sound_level", zone=self.zone, unit="dBA")
        Sensor.objects.create(node_id="sound-2", sensor_type="sound_level", zone=self.other_zone, unit="dBA")
        self.t0 = timezone.now() - timedelta(minutes=30)
        self.counter = 0
        self.pipeline = SensorPipeline()

    def ingest(self, value, minutes=None, node="sound-1", zone=None):
        zone = zone or self.zone
        self.counter += 1
        return self.pipeline.ingest(
            node_id=node,
            observation_type="sound_level",
            value=value,
            unit="dBA",
            observed_at=self.t0 + timedelta(minutes=self.counter if minutes is None else minutes),
            metadata={"zone": {"id": zone.code, "label": zone.name}},
        )

    def rule(self, **overrides):
        values = dict(name="Bruit", metric="sound_level", operator="gt", threshold=70, severity="warning")
        values.update(overrides)
        return AlarmRule.objects.create(**values)

    def active_alerts(self, rule):
        return Alert.objects.filter(rule=rule, active=True)

    def change(self, rule, *fields, action="updated"):
        """Publie l'événement ``alarm_rule.changed``, comme le module Database."""
        payload = {
            "rule_id": rule.pk,
            "action": action,
            "changed_fields": list(fields),
            "enabled": rule.enabled,
            "severity": rule.severity,
        }
        Messaging.current().publisher().publish(
            Topics.database_events(),
            Event(type=EventTypes.ALARM_RULE_CHANGED, payload=payload, source="database"),
        )

    def test_trigger_once_then_resolve(self):
        rule = self.rule(hysteresis=5)
        self.ingest(60)
        self.assertFalse(Alert.objects.filter(rule=rule).exists())

        self.ingest(75)
        self.ingest(80)
        latest = self.ingest(68)  # sous le seuil mais dans la marge d'hystérésis
        alerts = Alert.objects.filter(rule=rule)
        self.assertEqual(alerts.count(), 1, "une situation persistante ne doit pas répéter l'alerte")
        alert = alerts.get()
        self.assertTrue(alert.active)
        self.assertEqual(alert.trigger_value, 75)
        self.assertEqual(alert.code, f"RULE_{rule.pk}")
        self.assertEqual(alert.observation_id, latest.pk)
        self.assertIn("> 70 dBA", alert.message)

        self.ingest(64)
        alert.refresh_from_db()
        self.assertFalse(alert.active)
        self.assertEqual(alert.resolution, Alert.Resolution.RETURNED_TO_NORMAL)
        self.assertIsNotNone(alert.resolved_at)

        self.ingest(90)
        self.assertEqual(Alert.objects.filter(rule=rule).count(), 2, "un nouvel épisode crée une nouvelle alerte")

    def test_minimum_duration_is_respected(self):
        rule = self.rule(min_duration_seconds=180)
        self.ingest(75, minutes=0)
        self.ingest(76, minutes=2)
        self.assertFalse(self.active_alerts(rule).exists())
        self.assertEqual(AlarmRuleState.objects.get(rule=rule).status, Status.PENDING)
        self.ingest(77, minutes=3)
        self.assertTrue(self.active_alerts(rule).exists())

    def test_short_peak_does_not_trigger_with_duration(self):
        rule = self.rule(min_duration_seconds=180)
        self.ingest(75, minutes=0)
        self.ingest(60, minutes=1)
        self.ingest(75, minutes=2)
        self.ingest(75, minutes=4)
        self.assertFalse(self.active_alerts(rule).exists())

    def test_zone_scope(self):
        local_rule = self.rule(zone=self.other_zone)
        global_rule = self.rule(name="Global")
        self.ingest(90)
        self.assertFalse(Alert.objects.filter(rule=local_rule).exists())
        self.assertEqual(self.active_alerts(global_rule).get().zone, self.zone)
        self.ingest(90, node="sound-2", zone=self.other_zone)
        self.assertTrue(self.active_alerts(local_rule).exists())
        self.assertEqual(self.active_alerts(global_rule).count(), 2)

    def test_disabled_rules_and_invalid_values_are_ignored(self):
        disabled = self.rule(enabled=False)
        enabled = self.rule(name="Actif")
        self.ingest(500)  # hors limites physiques (0 à 150 dBA) : invalide
        self.assertFalse(Alert.objects.filter(rule__isnull=False).exists())
        self.ingest(90)
        self.assertFalse(Alert.objects.filter(rule=disabled).exists())
        self.assertTrue(self.active_alerts(enabled).exists())

    def test_out_of_order_observation_is_ignored(self):
        rule = self.rule()
        self.ingest(90, minutes=10)
        self.ingest(10, minutes=5)  # message en retard
        self.assertTrue(self.active_alerts(rule).exists())

    def test_rule_changes_resolve_current_alerts(self):
        rule = self.rule()
        self.ingest(90)
        alert = self.active_alerts(rule).get()

        AlarmRule.objects.filter(pk=rule.pk).update(severity="critical")
        rule.refresh_from_db()
        self.change(rule, "severity")
        alert.refresh_from_db()
        self.assertEqual((alert.active, alert.severity), (True, "critical"))

        AlarmRule.objects.filter(pk=rule.pk).update(threshold=95)
        rule.refresh_from_db()
        self.change(rule, "threshold")
        alert.refresh_from_db()
        self.assertEqual((alert.active, alert.resolution), (False, Alert.Resolution.RULE_UPDATED))
        self.assertFalse(AlarmRuleState.objects.filter(rule=rule).exists())

        self.ingest(96)
        AlarmRule.objects.filter(pk=rule.pk).update(enabled=False)
        rule.refresh_from_db()
        self.change(rule, "enabled")
        self.assertEqual(Alert.objects.filter(rule=rule, resolution=Alert.Resolution.RULE_DISABLED).count(), 1)

    def test_data_quality_alerts_still_work_independently(self):
        self.ingest(500)
        self.assertTrue(Alert.objects.filter(code="DATA_QUALITY_SOUND_LEVEL", active=True, rule=None).exists())
        self.ingest(60)
        self.assertFalse(Alert.objects.filter(code="DATA_QUALITY_SOUND_LEVEL", active=True).exists())

