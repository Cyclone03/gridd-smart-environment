from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from modules.alarms.domain.alarm_state_machine import AlarmStateMachine
from modules.alarms.domain.condition_evaluator import ConditionEvaluator
from modules.alarms.domain.condition_formatter import ConditionFormatter
from modules.alarms.domain.rule_change_policy import RuleChangePolicy
from modules.database.models import AlarmRuleState, Alert

Status = AlarmRuleState.Status


class ConditionTests(SimpleTestCase):
    def test_operators(self):
        met = ConditionEvaluator.condition_met
        self.assertTrue(met("gt", 31, 30))
        self.assertFalse(met("gt", 30, 30))
        self.assertTrue(met("gte", 30, 30))
        self.assertTrue(met("lt", 29, 30))
        self.assertTrue(met("lte", 30, 30))
        self.assertTrue(met("outside_range", 29.9, 30, 60))
        self.assertTrue(met("outside_range", 61, 30, 60))
        self.assertFalse(met("outside_range", 45, 30, 60))
        self.assertTrue(met("inside_range", 30, 30, 60))
        self.assertFalse(met("inside_range", 61, 30, 60))
        with self.assertRaises(ValueError):
            met("eq", 1, 1)

    def test_hysteresis_delays_return_to_normal(self):
        back = ConditionEvaluator.back_to_normal
        self.assertFalse(back("gt", 29.5, 30, hysteresis=1))
        self.assertTrue(back("gt", 29, 30, hysteresis=1))
        self.assertTrue(back("gt", 30, 30, hysteresis=0))
        self.assertFalse(back("lt", 10.5, 10, hysteresis=1))
        self.assertTrue(back("lt", 11, 10, hysteresis=1))
        self.assertFalse(back("outside_range", 30.5, 30, 60, hysteresis=1))
        self.assertTrue(back("outside_range", 31, 30, 60, hysteresis=1))
        self.assertFalse(back("inside_range", 29.5, 30, 60, hysteresis=1))
        self.assertTrue(back("inside_range", 28.9, 30, 60, hysteresis=1))

    def test_descriptions(self):
        describe = ConditionFormatter.describe
        self.assertEqual(describe("gt", 30, None, "°C"), "> 30 °C")
        self.assertEqual(describe("outside_range", 30, 60.5, "%"), "hors de [30 ; 60,5] %")
        self.assertEqual(describe("gte", 25.0, None, "personnes", integer=True), "≥ 25 personnes")


class TransitionTests(SimpleTestCase):
    def setUp(self):
        self.t0 = timezone.now()
        self.machine = AlarmStateMachine()

    def step(self, status, pending_since, breached, cleared=None, seconds=0, duration=0):
        return self.machine.next(
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


class RuleChangePolicyTests(SimpleTestCase):
    def setUp(self):
        self.policy = RuleChangePolicy()

    def test_decisions(self):
        self.assertEqual(self.policy.decide("deleted", [], True).resolution, Alert.Resolution.RULE_DELETED)
        self.assertEqual(self.policy.decide("updated", ["enabled"], False).resolution, Alert.Resolution.RULE_DISABLED)
        self.assertEqual(self.policy.decide("updated", ["threshold"], True).resolution, Alert.Resolution.RULE_UPDATED)
        self.assertTrue(self.policy.decide("updated", ["severity"], True).propagate_severity)
        self.assertIsNone(self.policy.decide("updated", ["name"], True).resolution)
        self.assertIsNone(self.policy.decide("created", [], True).resolution)
