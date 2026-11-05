from django.utils.dateparse import parse_datetime

from modules.alarms.domain.alarm_state_machine import AlarmStateMachine
from modules.alarms.domain.alert_codes import AlertCodes
from modules.alarms.domain.rule_state import RuleState
from modules.database.models import Alert, Observation


class RuleEvaluationService:
    """Applique les règles d'alarme actives à chaque observation persistée.

    - une seule alerte active par (règle, zone) : une situation qui persiste
      met à jour l'alerte existante au lieu d'en créer une nouvelle ;
    - les mesures invalides n'alimentent pas les règles (elles déclenchent
      déjà une alerte de qualité) ;
    - une mesure plus ancienne que la dernière mesure évaluée est ignorée
      (messages rejoués ou arrivés en retard).

    Les décisions sont publiées ; le module Database les enregistre.
    """

    ALL_FIELDS = ("observation", "message", "severity", "trigger_value")

    def __init__(self, *, rules, states, producer, evaluator, machine, messages):
        self._rules = rules
        self._states = states
        self._producer = producer
        self._evaluator = evaluator
        self._machine = machine
        self._messages = messages

    def evaluate(self, observation) -> list[tuple[str, int]]:
        if observation["quality_status"] == Observation.QualityStatus.INVALID:
            return []

        zone_code = observation["zone_code"]
        value = observation["value"]
        observed_at = parse_datetime(observation["observed_at"] or observation["received_at"])
        events = []

        for rule in self._rules.active_for(zone_code, observation["type"]):
            state = self._states.get(rule.id, zone_code)
            if state.last_observed_at and observed_at < state.last_observed_at:
                continue

            transition = self._machine.next(
                state.status,
                state.pending_since,
                breached=self._evaluator.condition_met(rule.operator, value, rule.threshold, rule.threshold_high),
                cleared=self._evaluator.back_to_normal(
                    rule.operator, value, rule.threshold, rule.threshold_high, rule.hysteresis
                ),
                observed_at=observed_at,
                min_duration_seconds=rule.min_duration_seconds,
            )
            self._publish_alert(transition.event, rule, observation)
            if transition.event in (AlarmStateMachine.TRIGGERED, AlarmStateMachine.RESOLVED):
                events.append((transition.event, rule.id))

            new_state = RuleState(transition.status, transition.pending_since, value, observed_at)
            self._states.remember(rule.id, zone_code, new_state)
            self._producer.state_saved(rule_id=rule.id, zone_code=zone_code, state=new_state)

        return events

    def _publish_alert(self, event, rule, observation):
        code = AlertCodes.for_rule(rule.id)
        if event == AlarmStateMachine.RESOLVED:
            self._producer.alert_resolved(
                zone_code=observation["zone_code"],
                code=code,
                resolution=Alert.Resolution.RETURNED_TO_NORMAL,
                observation_id=observation["id"],
            )
        elif event in (AlarmStateMachine.TRIGGERED, AlarmStateMachine.ONGOING):
            # « En cours » : rafraîchit l'alerte existante ou la recrée si elle
            # a disparu (clôturée manuellement, par exemple).
            self._producer.alert_raised(
                zone_code=observation["zone_code"],
                code=code,
                rule_id=rule.id,
                severity=rule.severity,
                message=self._messages.rule_message(rule, observation["zone_name"], observation["value"]),
                trigger_value=observation["value"],
                observation_id=observation["id"],
                refresh_fields=self.ALL_FIELDS if event == AlarmStateMachine.TRIGGERED else ("observation",),
            )
