from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from core.alarm_engine import (
    back_to_normal,
    condition_met,
    describe_condition,
    next_transition,
    on_rule_changed,
)
from core.models import AlarmRule, AlarmRuleState, Alert, Sensor, ThresholdProfile, Zone
from core.services import ingest_observation


Status = AlarmRuleState.Status


class ConditionTests(SimpleTestCase):
    def test_operators(self):
        self.assertTrue(condition_met("gt", 31, 30))
        self.assertFalse(condition_met("gt", 30, 30))
        self.assertTrue(condition_met("gte", 30, 30))
        self.assertTrue(condition_met("lt", 29, 30))
        self.assertTrue(condition_met("lte", 30, 30))
        self.assertTrue(condition_met("outside_range", 29.9, 30, 60))
        self.assertTrue(condition_met("outside_range", 61, 30, 60))
        self.assertFalse(condition_met("outside_range", 45, 30, 60))
        self.assertTrue(condition_met("inside_range", 30, 30, 60))
        self.assertFalse(condition_met("inside_range", 61, 30, 60))
        with self.assertRaises(ValueError):
            condition_met("eq", 1, 1)

    def test_hysteresis_delays_return_to_normal(self):
        self.assertFalse(back_to_normal("gt", 29.5, 30, hysteresis=1))
        self.assertTrue(back_to_normal("gt", 29, 30, hysteresis=1))
        self.assertTrue(back_to_normal("gt", 30, 30, hysteresis=0))
        self.assertFalse(back_to_normal("lt", 10.5, 10, hysteresis=1))
        self.assertTrue(back_to_normal("lt", 11, 10, hysteresis=1))
        self.assertFalse(back_to_normal("outside_range", 30.5, 30, 60, hysteresis=1))
        self.assertTrue(back_to_normal("outside_range", 31, 30, 60, hysteresis=1))
        self.assertFalse(back_to_normal("inside_range", 29.5, 30, 60, hysteresis=1))
        self.assertTrue(back_to_normal("inside_range", 28.9, 30, 60, hysteresis=1))

    def test_descriptions(self):
        self.assertEqual(describe_condition("gt", 30, None, "°C"), "> 30 °C")
        self.assertEqual(describe_condition("outside_range", 30, 60.5, "%"), "hors de [30 ; 60,5] %")
        self.assertEqual(describe_condition("gte", 25.0, None, "personnes", integer=True), "≥ 25 personnes")


class TransitionTests(SimpleTestCase):
    def setUp(self):
        self.t0 = timezone.now()

    def step(self, status, pending_since, breached, cleared=None, seconds=0, duration=0):
        return next_transition(
            status,
            pending_since,
            breached=breached,
            cleared=(not breached) if cleared is None else cleared,
            observed_at=self.t0 + timedelta(seconds=seconds),
            min_duration_seconds=duration,
        )

    def test_immediate_trigger_and_resolution(self):
        self.assertEqual(self.step(Status.NORMAL, None, True).event, "triggered")
        self.assertEqual(self.step(Status.ACTIVE, None, True).event, "ongoing")
        self.assertEqual(self.step(Status.ACTIVE, None, False).event, "resolved")

    def test_minimum_duration(self):
        first = self.step(Status.NORMAL, None, True, duration=60)
        self.assertEqual((first.status, first.event), (Status.PENDING, None))
        early = self.step(Status.PENDING, first.pending_since, True, seconds=30, duration=60)
        self.assertEqual(early.status, Status.PENDING)
        self.assertEqual(early.pending_since, first.pending_since)
        late = self.step(Status.PENDING, first.pending_since, True, seconds=60, duration=60)
        self.assertEqual((late.status, late.event), (Status.ACTIVE, "triggered"))

    def test_pending_condition_that_stops_returns_to_normal(self):
        interrupted = self.step(Status.PENDING, self.t0, False, seconds=30, duration=60)
        self.assertEqual((interrupted.status, interrupted.pending_since), (Status.NORMAL, None))


class EngineIntegrationTests(TestCase):
    """Évaluation réelle via ``ingest_observation`` (comme Kafka ou le simulateur)."""

    def setUp(self):
        self.zone = Zone.objects.create(name="Salle de réunion", code="meeting-room")
        self.other_zone = Zone.objects.create(name="Bureau", code="office")
        # Profil désactivé : pas d'alerte de variation rapide parasite.
        ThresholdProfile.objects.create(zone=self.zone, enabled=False)
        ThresholdProfile.objects.create(zone=self.other_zone, enabled=False)
        Sensor.objects.create(node_id="sound-1", sensor_type="sound_level", zone=self.zone, unit="dBA")
        Sensor.objects.create(node_id="sound-2", sensor_type="sound_level", zone=self.other_zone, unit="dBA")
        self.t0 = timezone.now() - timedelta(minutes=30)
        self.counter = 0

    def ingest(self, value, minutes=None, node="sound-1", zone=None):
        zone = zone or self.zone
        self.counter += 1
        return ingest_observation(
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

        rule.severity = "critical"
        rule.save()
        on_rule_changed(rule, ["severity"])
        alert.refresh_from_db()
        self.assertEqual((alert.active, alert.severity), (True, "critical"))

        rule.threshold = 95
        rule.save()
        on_rule_changed(rule, ["threshold"])
        alert.refresh_from_db()
        self.assertEqual((alert.active, alert.resolution), (False, Alert.Resolution.RULE_UPDATED))
        self.assertFalse(AlarmRuleState.objects.filter(rule=rule).exists())

        self.ingest(96)
        rule.enabled = False
        rule.save()
        on_rule_changed(rule, ["enabled"])
        self.assertEqual(
            Alert.objects.filter(rule=rule, resolution=Alert.Resolution.RULE_DISABLED).count(),
            1,
        )

    def test_data_quality_alerts_still_work_independently(self):
        self.ingest(500)
        self.assertTrue(Alert.objects.filter(code="DATA_QUALITY_SOUND_LEVEL", active=True, rule=None).exists())
        self.ingest(60)
        self.assertFalse(Alert.objects.filter(code="DATA_QUALITY_SOUND_LEVEL", active=True).exists())
