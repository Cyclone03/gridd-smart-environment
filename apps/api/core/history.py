"""Sélection de période et agrégation de l'historique des mesures.

Contrat de ``GET /api/zones/<code>/history/`` (voir docs/api.md) :

- ``start`` et ``end`` (ISO 8601, avec fuseau de préférence) : période
  arbitraire, bornée par ``HISTORY_MAX_RANGE_DAYS`` ;
- ``bucket_minutes`` (facultatif) : granularité d'agrégation parmi
  ``BUCKET_CHOICES_MINUTES``. Absente, elle est choisie pour produire environ
  ``HISTORY_TARGET_POINTS`` points ;
- modes historiques conservés pour compatibilité : ``hours`` (1, 6, 24, 168)
  ou ``date`` (AAAA-MM-JJ, journée locale complète).

Les dates sans fuseau sont interprétées dans le fuseau du serveur
(``TIME_ZONE``). Les réponses sont exprimées dans ce même fuseau.
"""

import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime


BUCKET_CHOICES_MINUTES = (1, 5, 15, 30, 60, 180, 360, 720, 1440)
LEGACY_HOURS = (1, 6, 24, 168)


class HistoryParamError(ValueError):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime
    bucket_minutes: int
    # Valeurs renvoyées pour compatibilité avec l'ancien contrat.
    hours: int
    date: str | None = None

    @property
    def span(self):
        return self.end - self.start


def choose_bucket_minutes(span, target_points):
    """Plus petite granularité produisant au plus ``target_points`` points."""
    span_minutes = span.total_seconds() / 60
    for bucket in BUCKET_CHOICES_MINUTES:
        if span_minutes / bucket <= target_points:
            return bucket
    return BUCKET_CHOICES_MINUTES[-1]


def _parse_instant(raw, field, tz):
    value = parse_datetime(raw.strip()) if raw else None
    if value is None:
        raise HistoryParamError(
            f"« {field} » doit être une date et heure ISO 8601 (ex. 2026-10-27T08:00:00-04:00).",
            field,
        )
    if timezone.is_naive(value):
        value = timezone.make_aware(value, tz)
    return value


def parse_period(params, *, now=None, tz=None):
    """Construit la période demandée à partir des paramètres de requête."""
    now = now or timezone.now()
    tz = tz or timezone.get_current_timezone()
    raw_start = params.get("start")
    raw_end = params.get("end")
    raw_bucket = params.get("bucket_minutes")

    if raw_start or raw_end:
        if not (raw_start and raw_end):
            raise HistoryParamError("Les paramètres « start » et « end » doivent être fournis ensemble.")
        start = _parse_instant(raw_start, "start", tz)
        end = _parse_instant(raw_end, "end", tz)
        if end <= start:
            raise HistoryParamError("La fin de la période doit être postérieure au début.", "end")
        max_span = timedelta(days=settings.HISTORY_MAX_RANGE_DAYS)
        if end - start > max_span:
            raise HistoryParamError(
                f"La période demandée dépasse la limite de {settings.HISTORY_MAX_RANGE_DAYS} jours.",
                "end",
            )
        if start > now:
            raise HistoryParamError("Le début de la période est dans le futur.", "start")

        if raw_bucket:
            try:
                bucket = int(raw_bucket)
            except ValueError as exc:
                raise HistoryParamError("« bucket_minutes » doit être un entier.", "bucket_minutes") from exc
            if bucket not in BUCKET_CHOICES_MINUTES:
                allowed = ", ".join(str(item) for item in BUCKET_CHOICES_MINUTES)
                raise HistoryParamError(
                    f"« bucket_minutes » doit valoir l'une de ces valeurs : {allowed}.",
                    "bucket_minutes",
                )
            points = math.ceil((end - start).total_seconds() / (bucket * 60))
            if points > settings.HISTORY_MAX_POINTS:
                raise HistoryParamError(
                    f"Granularité trop fine : {points} points demandés "
                    f"(maximum {settings.HISTORY_MAX_POINTS}).",
                    "bucket_minutes",
                )
        else:
            bucket = choose_bucket_minutes(end - start, settings.HISTORY_TARGET_POINTS)

        hours = max(1, round((end - start).total_seconds() / 3600))
        return Period(start=start, end=end, bucket_minutes=bucket, hours=hours)

    requested_date = params.get("date")
    if requested_date:
        try:
            selected_date = datetime.strptime(requested_date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise HistoryParamError("La date doit respecter le format AAAA-MM-JJ.", "date") from exc
        start = timezone.make_aware(datetime.combine(selected_date, time.min), tz)
        end = timezone.make_aware(datetime.combine(selected_date + timedelta(days=1), time.min), tz)
        return Period(start=start, end=end, bucket_minutes=15, hours=24, date=requested_date)

    try:
        hours = int(params.get("hours", "24"))
    except ValueError as exc:
        raise HistoryParamError("La période doit être un nombre d'heures.", "hours") from exc
    if hours not in LEGACY_HOURS:
        raise HistoryParamError("Période permise : 1, 6, 24 ou 168 heures.", "hours")
    bucket = 5 if hours <= 6 else 15 if hours <= 24 else 60
    return Period(start=now - timedelta(hours=hours), end=now, bucket_minutes=bucket, hours=hours)


def bucket_start(measured_at, bucket_minutes, tz):
    """Début du créneau local contenant ``measured_at``.

    Les créneaux sont alignés sur l'heure locale (minuit pour les créneaux
    d'un jour), toutes les granularités divisant exactement 24 h.
    """
    local = timezone.localtime(measured_at, tz)
    minutes = local.hour * 60 + local.minute
    floored = minutes - minutes % bucket_minutes
    return local.replace(hour=floored // 60, minute=floored % 60, second=0, microsecond=0)


def aggregate(rows, bucket_minutes, tz, normal_status="normal"):
    """Regroupe des mesures ``{value, observed_at, received_at, quality_status}``.

    Retourne les points (moyenne, minimum, maximum, nombre, mesures
    suspectes par créneau) triés chronologiquement et la liste des valeurs.
    """
    buckets = {}
    values = []
    for row in rows:
        measured_at = row["observed_at"] or row["received_at"]
        start = bucket_start(measured_at, bucket_minutes, tz)
        bucket = buckets.setdefault(start, {"values": [], "suspicious": 0})
        value = float(row["value"])
        bucket["values"].append(value)
        values.append(value)
        if row["quality_status"] != normal_status:
            bucket["suspicious"] += 1

    points = []
    for start in sorted(buckets):
        bucket_values = buckets[start]["values"]
        points.append(
            {
                "time": start.isoformat(),
                "average": round(sum(bucket_values) / len(bucket_values), 2),
                "minimum": min(bucket_values),
                "maximum": max(bucket_values),
                "count": len(bucket_values),
                "suspicious_count": buckets[start]["suspicious"],
            }
        )
    return points, values


def compute_trend(points, tolerance):
    if len(points) < 2:
        return "stable"
    delta = points[-1]["average"] - points[0]["average"]
    if delta > tolerance:
        return "rising"
    if delta < -tolerance:
        return "falling"
    return "stable"
