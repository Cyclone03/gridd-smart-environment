"""Évaluation des règles d'alarme configurables.

Le moteur est appelé par ``core.services.ingest_observation`` pour chaque
nouvelle mesure, quelle que soit sa source (Kafka, simulateur). Il ne dépend
donc pas de l'ouverture d'une page dans le navigateur.

Cycle de vie d'une règle pour une zone (``AlarmRuleState``) :

    NORMAL ──condition vraie──► PENDING ──durée minimale atteinte──► ACTIVE
       ▲            │ (durée 0 : passage direct à ACTIVE)               │
       └─condition fausse─┘                                             │
       ▲                                                                │
       └──────────── retour à la normale (avec hystérésis) ◄────────────┘

- Une seule alerte active par (règle, zone) : une situation qui persiste ne
  crée pas d'alertes répétées, elle met à jour l'alerte existante.
- L'hystérésis évite les oscillations autour d'un seuil unique.
- Les mesures invalides (hors limites physiques) n'alimentent pas les règles :
  elles déclenchent déjà une alerte de qualité des données.
- Une mesure plus ancienne que la dernière mesure évaluée est ignorée
  (messages Kafka rejoués ou arrivés en retard).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from . import metrics
from .models import AlarmRule, AlarmRuleState, Alert, Observation
from .realtime import schedule_alerts_changed


Status = AlarmRuleState.Status

# Champs dont la modification change la condition : les états et alertes
# en cours sont alors réinitialisés (voir ``on_rule_changed``).
CONDITION_FIELDS = frozenset(
    {
        "zone",
        "metric",
        "operator",
        "threshold",
        "threshold_high",
        "min_duration_seconds",
        "hysteresis",
    }
)


# ---------------------------------------------------------------------------
# Fonctions pures (testables sans base de données)
# ---------------------------------------------------------------------------


def condition_met(operator, value, threshold, threshold_high=None):
    """Indique si ``value`` est en situation d'alarme pour la condition."""
    if operator == metrics.OPERATOR_GT:
        return value > threshold
    if operator == metrics.OPERATOR_GTE:
        return value >= threshold
    if operator == metrics.OPERATOR_LT:
        return value < threshold
    if operator == metrics.OPERATOR_LTE:
        return value <= threshold
    if operator == metrics.OPERATOR_OUTSIDE_RANGE:
        return value < threshold or value > threshold_high
    if operator == metrics.OPERATOR_INSIDE_RANGE:
        return threshold <= value <= threshold_high
    raise ValueError(f"Opérateur inconnu : {operator}")


def back_to_normal(operator, value, threshold, threshold_high=None, hysteresis=0.0):
    """Indique si une alarme active peut être résolue.

    L'hystérésis repousse le seuil de retour à la normale vers la zone saine :
    « > 30 » avec 1 d'hystérésis se résout à 29 ou moins ; « hors de
    [30 ; 60] » se résout entre 31 et 59.
    """
    h = hysteresis or 0.0
    if operator in (metrics.OPERATOR_GT, metrics.OPERATOR_GTE):
        return value <= threshold - h if h else not condition_met(operator, value, threshold)
    if operator in (metrics.OPERATOR_LT, metrics.OPERATOR_LTE):
        return value >= threshold + h if h else not condition_met(operator, value, threshold)
    if operator == metrics.OPERATOR_OUTSIDE_RANGE:
        return threshold + h <= value <= threshold_high - h
    if operator == metrics.OPERATOR_INSIDE_RANGE:
        return value < threshold - h or value > threshold_high + h
    raise ValueError(f"Opérateur inconnu : {operator}")


@dataclass(frozen=True)
class Transition:
    status: str
    pending_since: datetime | None
    # "triggered", "resolved", "ongoing" (alarme maintenue) ou None.
    event: str | None


def next_transition(status, pending_since, *, breached, cleared, observed_at, min_duration_seconds):
    """Calcule le nouvel état d'une règle pour une mesure donnée."""
    if status == Status.ACTIVE:
        if cleared:
            return Transition(Status.NORMAL, None, "resolved")
        return Transition(Status.ACTIVE, None, "ongoing")

    if not breached:
        return Transition(Status.NORMAL, None, None)

    if min_duration_seconds <= 0:
        return Transition(Status.ACTIVE, None, "triggered")

    started = pending_since if status == Status.PENDING and pending_since else observed_at
    if observed_at - started >= timedelta(seconds=min_duration_seconds):
        return Transition(Status.ACTIVE, None, "triggered")
    return Transition(Status.PENDING, started, None)


def format_number(value, integer=False):
    if integer:
        return str(int(round(value)))
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def describe_condition(operator, threshold, threshold_high, unit, integer=False):
    """Libellé lisible d'une condition, ex. « > 30 °C » ou « hors de [30 ; 60] % »."""
    low = format_number(threshold, integer)
    suffix = f" {unit}" if unit else ""
    if operator in metrics.OPERATOR_SYMBOLS:
        return f"{metrics.OPERATOR_SYMBOLS[operator]} {low}{suffix}"
    high = format_number(threshold_high, integer)
    if operator == metrics.OPERATOR_OUTSIDE_RANGE:
        return f"hors de [{low} ; {high}]{suffix}"
    return f"dans [{low} ; {high}]{suffix}"


def describe_rule(rule):
    definition = metrics.get_metric(rule.metric)
    return describe_condition(
        rule.operator,
        rule.threshold,
        rule.threshold_high,
        rule.unit,
        integer=bool(definition and definition.integer),
    )


# ---------------------------------------------------------------------------
# Évaluation avec persistance
# ---------------------------------------------------------------------------


def rules_for_observation(observation):
    return AlarmRule.objects.filter(
        enabled=True,
        metric=observation.type,
    ).filter(Q(zone=observation.zone) | Q(zone__isnull=True))


def _alert_message(rule, observation):
    definition = metrics.get_metric(rule.metric)
    value = format_number(observation.value, bool(definition and definition.integer))
    return (
        f"{rule.name} — {observation.zone.name} : {value} {rule.unit} "
        f"(condition {describe_rule(rule)})"
    )[:255]


def evaluate_alarm_rules(observation):
    """Applique toutes les règles actives concernées par ``observation``.

    Doit être appelée dans la transaction d'ingestion. Retourne la liste des
    événements produits (utile pour les journaux et les tests).
    """
    if observation.quality_status == Observation.QualityStatus.INVALID:
        return []

    observed_at = observation.observed_at or observation.received_at
    events = []

    for rule in rules_for_observation(observation):
        state, _ = AlarmRuleState.objects.select_for_update().get_or_create(
            rule=rule,
            zone=observation.zone,
        )
        if state.last_observed_at and observed_at < state.last_observed_at:
            continue

        transition = next_transition(
            state.status,
            state.pending_since,
            breached=condition_met(rule.operator, observation.value, rule.threshold, rule.threshold_high),
            cleared=back_to_normal(
                rule.operator,
                observation.value,
                rule.threshold,
                rule.threshold_high,
                rule.hysteresis,
            ),
            observed_at=observed_at,
            min_duration_seconds=rule.min_duration_seconds,
        )

        active_alert = Alert.objects.filter(rule=rule, zone=observation.zone, active=True).first()

        if transition.event == "triggered" or (transition.event == "ongoing" and active_alert is None):
            Alert.objects.create(
                zone=observation.zone,
                observation=observation,
                rule=rule,
                code=rule.alert_code,
                severity=rule.severity,
                message=_alert_message(rule, observation),
                trigger_value=observation.value,
            )
            schedule_alerts_changed()
            events.append(("triggered", rule.pk))
        elif transition.event == "ongoing":
            active_alert.observation = observation
            active_alert.save(update_fields=["observation"])
        elif transition.event == "resolved":
            if active_alert:
                active_alert.active = False
                active_alert.resolved_at = timezone.now()
                active_alert.resolution = Alert.Resolution.RETURNED_TO_NORMAL
                active_alert.observation = observation
                active_alert.save(update_fields=["active", "resolved_at", "resolution", "observation"])
                schedule_alerts_changed()
            events.append(("resolved", rule.pk))

        state.status = transition.status
        state.pending_since = transition.pending_since
        state.last_value = observation.value
        state.last_observed_at = observed_at
        state.save(update_fields=["status", "pending_since", "last_value", "last_observed_at", "updated_at"])

    return events


# ---------------------------------------------------------------------------
# Changements de configuration
# ---------------------------------------------------------------------------


def resolve_rule_alerts(rule, resolution):
    """Clôt les alertes actives d'une règle et remet ses états à zéro."""
    closed = Alert.objects.filter(rule=rule, active=True).update(
        active=False,
        resolved_at=timezone.now(),
        resolution=resolution,
    )
    AlarmRuleState.objects.filter(rule=rule).delete()
    if closed:
        schedule_alerts_changed()
    return closed


@transaction.atomic
def on_rule_changed(rule, changed_fields):
    """Applique les effets d'une modification de règle.

    - Désactivation : les alertes en cours sont résolues (« règle désactivée »).
    - Modification de la condition : les alertes en cours sont résolues
      (« règle modifiée ») et la règle sera réévaluée à la prochaine mesure.
    - Changement de gravité seul : répercuté sur les alertes en cours.
    """
    if "enabled" in changed_fields and not rule.enabled:
        return resolve_rule_alerts(rule, Alert.Resolution.RULE_DISABLED)
    if CONDITION_FIELDS & set(changed_fields):
        return resolve_rule_alerts(rule, Alert.Resolution.RULE_UPDATED)
    if "severity" in changed_fields:
        updated = Alert.objects.filter(rule=rule, active=True).update(severity=rule.severity)
        if updated:
            schedule_alerts_changed()
    return 0


@transaction.atomic
def delete_rule(rule):
    resolve_rule_alerts(rule, Alert.Resolution.RULE_DELETED)
    rule.delete()
