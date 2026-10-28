"""Ingestion des observations et contrôle de qualité des données.

Point d'entrée unique : ``ingest_observation``. Il est appelé par le consumer
Kafka et par le simulateur, et enchaîne dans une même transaction :

1. rattachement à la zone et au capteur (créés au besoin) ;
2. vérification de l'unité et de la valeur ;
3. évaluation de la qualité (valeur impossible, variation rapide, capteur
   bloqué) et alerte de qualité associée ;
4. évaluation des règles d'alarme configurables (``core.alarm_engine``) ;
5. diffusion temps réel après validation de la transaction.
"""

import logging

from django.db import transaction
from django.utils import timezone

from . import metrics
from .alarm_engine import evaluate_alarm_rules
from .models import (
    Alert,
    Observation,
    Sensor,
    ThresholdProfile,
    Zone,
)
from .realtime import broadcast_observation, observation_payload, schedule_alerts_changed


logger = logging.getLogger(__name__)


def infer_zone_type(zone_id):
    if zone_id == "server-equipment-room":
        return Zone.ZoneType.SERVER_ROOM

    if zone_id == "professors-office":
        return Zone.ZoneType.OFFICE

    if zone_id == "meeting-room":
        return Zone.ZoneType.MEETING_ROOM

    if zone_id == "open-workspace":
        return Zone.ZoneType.OPEN_WORKSPACE

    if zone_id.startswith(
        "individual-work-cubicle"
    ):
        return Zone.ZoneType.CUBICLE

    return Zone.ZoneType.OTHER


def get_or_create_zone_from_metadata(
    *,
    metadata,
    node_id,
):
    zone_metadata = metadata.get(
        "zone",
        {},
    )

    zone_id = zone_metadata.get(
        "id",
    ) or node_id

    zone_label = zone_metadata.get(
        "label",
    )

    if not zone_id:
        zone_id = node_id

    expected_type = infer_zone_type(
        zone_id
    )

    zone, _ = Zone.objects.get_or_create(
        code=zone_id,
        defaults={
            "name": zone_label or zone_id,
            "zone_type": expected_type,
        },
    )

    changed_fields = []

    if (
        zone_label
        and zone.name != zone_label
    ):
        zone.name = zone_label
        changed_fields.append(
            "name"
        )

    if (
        expected_type != Zone.ZoneType.OTHER
        and zone.zone_type != expected_type
    ):
        zone.zone_type = expected_type
        changed_fields.append(
            "zone_type"
        )

    if changed_fields:
        zone.save(
            update_fields=changed_fields
        )

    # Chaque vraie zone reçoit automatiquement
    # un profil configurable.
    ThresholdProfile.objects.get_or_create(
        zone=zone,
        defaults={
            "enabled": False,
        },
    )

    return zone


def get_or_create_sensor(
    *,
    node_id,
    observation_type,
    unit,
    zone,
    metadata,
):
    sensor, created = Sensor.objects.get_or_create(
        node_id=node_id,
        sensor_type=observation_type,
        defaults={
            "label": (
                f"{node_id} - "
                f"{observation_type}"
            ),
            "zone": zone,
            "unit": unit,
            "metadata": metadata,
            "active": True,
        },
    )

    if not sensor.active:
        raise ValueError(
            f"capteur désactivé: {node_id}"
        )

    if sensor.zone_id != zone.id:
        raise ValueError(
            f"zone incohérente pour "
            f"{node_id}/{observation_type}: "
            f"base={sensor.zone.code}, "
            f"kafka={zone.code}"
        )

    if sensor.unit != unit:
        raise ValueError(
            f"unité incohérente pour "
            f"{node_id}/{observation_type}: "
            f"base={sensor.unit}, "
            f"kafka={unit}"
        )

    if (
        not created
        and sensor.metadata != metadata
    ):
        sensor.metadata = metadata
        sensor.save(
            update_fields=[
                "metadata",
            ]
        )

    return sensor


def _latest_previous(
    sensor,
    observed_at,
):
    queryset = Observation.objects.filter(
        sensor=sensor
    )

    if observed_at:
        queryset = queryset.filter(
            observed_at__lt=observed_at
        )

    return queryset.order_by(
        "-observed_at",
        "-received_at",
    ).first()


def assess_quality(
    sensor,
    value,
    observed_at,
):
    numeric_value = float(value)
    definition = metrics.get_metric(sensor.sensor_type)
    plausible_range = definition.plausible_range if definition else None
    if plausible_range:
        minimum, maximum = plausible_range
        if not minimum <= numeric_value <= maximum:
            return (
                Observation.QualityStatus.INVALID,
                f"valeur hors limites physiques: {value} (attendu {minimum} à {maximum})",
            )

    profile = getattr(
        sensor.zone,
        "threshold_profile",
        None,
    )

    previous = _latest_previous(
        sensor,
        observed_at,
    )

    if not previous:
        return (
            Observation.QualityStatus.NORMAL,
            "",
        )

    current_time = (
        observed_at
        or timezone.now()
    )

    previous_time = (
        previous.observed_at
        or previous.received_at
    )

    elapsed_seconds = (
        current_time
        - previous_time
    ).total_seconds()

    if elapsed_seconds < -300:
        return (
            Observation.QualityStatus.INVALID,
            "horodatage antérieur à la dernière mesure du capteur",
        )

    recent = list(
        Observation.objects.filter(sensor=sensor)
        .order_by("-observed_at", "-received_at")[:100]
    )
    oldest_unchanged_time = None
    for item in recent:
        if item.value != numeric_value:
            break
        oldest_unchanged_time = item.observed_at or item.received_at
    if oldest_unchanged_time:
        unchanged_minutes = max(
            (current_time - oldest_unchanged_time).total_seconds() / 60.0,
            0,
        )
        stuck_after = profile.stuck_after_minutes if profile else 15
        if unchanged_minutes >= stuck_after:
            return (
                Observation.QualityStatus.SUSPICIOUS,
                f"valeur inchangée depuis {unchanged_minutes:.0f} min",
            )

    if not profile or not profile.enabled:
        return (
            Observation.QualityStatus.NORMAL,
            "",
        )

    minutes = max(
        elapsed_seconds / 60.0,
        1 / 60,
    )

    delta_per_minute = (
        abs(
            numeric_value
            - previous.value
        )
        / minutes
    )

    limits = {
        "temperature":
            profile.max_temperature_delta_per_minute,

        "humidity":
            profile.max_humidity_delta_per_minute,
    }

    limit = limits.get(
        sensor.sensor_type
    )

    if (
        limit is not None
        and delta_per_minute > limit
    ):
        return (
            Observation.QualityStatus.SUSPICIOUS,
            (
                f"variation rapide: "
                f"{delta_per_minute:.2f}/min "
                f"> {limit:.2f}/min"
            ),
        )

    return (
        Observation.QualityStatus.NORMAL,
        "",
    )


def _sync_quality_alert(observation):
    code = f"DATA_QUALITY_{observation.type.upper()}"
    active_alert = Alert.objects.filter(
        zone=observation.zone,
        code=code,
        active=True,
    ).first()

    if observation.quality_status == Observation.QualityStatus.NORMAL:
        if active_alert:
            active_alert.active = False
            active_alert.resolved_at = timezone.now()
            active_alert.resolution = Alert.Resolution.RETURNED_TO_NORMAL
            active_alert.save(update_fields=["active", "resolved_at", "resolution"])
            schedule_alerts_changed()
        return

    severity = (
        Alert.Severity.CRITICAL
        if observation.quality_status == Observation.QualityStatus.INVALID
        else Alert.Severity.WARNING
    )
    message = (
        f"Donnée {observation.get_quality_status_display().lower()} pour "
        f"{observation.zone.name}: {observation.quality_reason}"
    )

    if active_alert:
        active_alert.observation = observation
        active_alert.message = message
        active_alert.severity = severity
        active_alert.save(update_fields=["observation", "message", "severity"])
    else:
        Alert.objects.create(
            zone=observation.zone,
            observation=observation,
            code=code,
            severity=severity,
            message=message,
            trigger_value=observation.value,
        )
        schedule_alerts_changed()


@transaction.atomic
def ingest_observation(
    *,
    node_id,
    observation_type,
    value,
    unit,
    observed_at=None,
    metadata=None,
):
    metadata = metadata or {}

    zone = get_or_create_zone_from_metadata(
        metadata=metadata,
        node_id=node_id,
    )

    sensor = get_or_create_sensor(
        node_id=node_id,
        observation_type=observation_type,
        unit=unit,
        zone=zone,
        metadata=metadata,
    )

    definition = metrics.get_metric(observation_type)
    expected_units = definition.accepted_units if definition else None

    if (
        expected_units
        and unit not in expected_units
    ):
        raise ValueError(
            f"unité incohérente pour "
            f"{observation_type}: {unit}"
        )

    try:
        numeric_value = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"valeur invalide: {value}"
        ) from exc

    (
        quality_status,
        quality_reason,
    ) = assess_quality(
        sensor,
        numeric_value,
        observed_at,
    )

    observation = Observation.objects.create(
        sensor=sensor,
        zone=zone,
        type=observation_type,
        value=numeric_value,
        unit=unit,
        observed_at=observed_at,
        metadata=metadata,
        quality_status=quality_status,
        quality_reason=quality_reason,
    )

    _sync_quality_alert(observation)
    evaluate_alarm_rules(observation)

    payload = observation_payload(observation)

    # Le navigateur ne doit recevoir que des données réellement validées.
    transaction.on_commit(lambda: broadcast_observation(payload))

    return observation
