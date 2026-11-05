import math
from datetime import datetime, time, timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .period import Period
from .period_param_error import PeriodParamError


class PeriodParser:
    """Construit la période demandée à partir des paramètres de requête.

    - ``start`` et ``end`` (ISO 8601) : période arbitraire, bornée par
      ``max_range_days`` ; ``bucket_minutes`` facultatif parmi ``BUCKET_CHOICES_MINUTES`` ;
      absente, la granularité vise ``target_points`` points ;
    - compatibilité : ``hours`` (1, 6, 24, 168) ou ``date`` (journée locale).

    Les dates sans fuseau sont interprétées dans le fuseau ``tz``.
    """

    BUCKET_CHOICES_MINUTES = (1, 5, 15, 30, 60, 180, 360, 720, 1440)
    LEGACY_HOURS = (1, 6, 24, 168)

    def __init__(self, *, max_range_days, target_points, max_points):
        self._max_range_days = max_range_days
        self._target_points = target_points
        self._max_points = max_points

    @classmethod
    def from_settings(cls) -> "PeriodParser":
        return cls(
            max_range_days=settings.HISTORY_MAX_RANGE_DAYS,
            target_points=settings.HISTORY_TARGET_POINTS,
            max_points=settings.HISTORY_MAX_POINTS,
        )

    @classmethod
    def choose_bucket_minutes(cls, span, target_points) -> int:
        """Plus petite granularité produisant au plus ``target_points`` points."""
        span_minutes = span.total_seconds() / 60
        for bucket in cls.BUCKET_CHOICES_MINUTES:
            if span_minutes / bucket <= target_points:
                return bucket
        return cls.BUCKET_CHOICES_MINUTES[-1]

    def parse(self, params, *, now=None, tz=None) -> Period:
        now = now or timezone.now()
        tz = tz or timezone.get_current_timezone()
        if params.get("start") or params.get("end"):
            return self._explicit(params, now, tz)
        if params.get("date"):
            return self._day(params["date"], tz)
        return self._legacy_hours(params.get("hours", "24"), now)

    def _explicit(self, params, now, tz):
        raw_start, raw_end = params.get("start"), params.get("end")
        if not (raw_start and raw_end):
            raise PeriodParamError("Les paramètres « start » et « end » doivent être fournis ensemble.")
        start = self._instant(raw_start, "start", tz)
        end = self._instant(raw_end, "end", tz)
        if end <= start:
            raise PeriodParamError("La fin de la période doit être postérieure au début.", "end")
        if end - start > timedelta(days=self._max_range_days):
            raise PeriodParamError(f"La période demandée dépasse la limite de {self._max_range_days} jours.", "end")
        if start > now:
            raise PeriodParamError("Le début de la période est dans le futur.", "start")

        raw_bucket = params.get("bucket_minutes")
        if raw_bucket:
            bucket = self._bucket(raw_bucket, start, end)
        else:
            bucket = self.choose_bucket_minutes(end - start, self._target_points)
        hours = max(1, round((end - start).total_seconds() / 3600))
        return Period(start=start, end=end, bucket_minutes=bucket, hours=hours)

    def _bucket(self, raw, start, end):
        try:
            bucket = int(raw)
        except ValueError as exc:
            raise PeriodParamError("« bucket_minutes » doit être un entier.", "bucket_minutes") from exc
        if bucket not in self.BUCKET_CHOICES_MINUTES:
            allowed = ", ".join(str(item) for item in self.BUCKET_CHOICES_MINUTES)
            raise PeriodParamError(f"« bucket_minutes » doit valoir l'une de ces valeurs : {allowed}.", "bucket_minutes")
        points = math.ceil((end - start).total_seconds() / (bucket * 60))
        if points > self._max_points:
            raise PeriodParamError(
                f"Granularité trop fine : {points} points demandés (maximum {self._max_points}).",
                "bucket_minutes",
            )
        return bucket

    @staticmethod
    def _day(raw, tz):
        try:
            selected = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError as exc:
            raise PeriodParamError("La date doit respecter le format AAAA-MM-JJ.", "date") from exc
        start = timezone.make_aware(datetime.combine(selected, time.min), tz)
        end = timezone.make_aware(datetime.combine(selected + timedelta(days=1), time.min), tz)
        return Period(start=start, end=end, bucket_minutes=15, hours=24, date=raw)

    def _legacy_hours(self, raw, now):
        try:
            hours = int(raw)
        except ValueError as exc:
            raise PeriodParamError("La période doit être un nombre d'heures.", "hours") from exc
        if hours not in self.LEGACY_HOURS:
            raise PeriodParamError("Période permise : 1, 6, 24 ou 168 heures.", "hours")
        bucket = 5 if hours <= 6 else 15 if hours <= 24 else 60
        return Period(start=now - timedelta(hours=hours), end=now, bucket_minutes=bucket, hours=hours)

    @staticmethod
    def _instant(raw, field, tz):
        value = parse_datetime(raw.strip()) if raw else None
        if value is None:
            raise PeriodParamError(
                f"« {field} » doit être une date et heure ISO 8601 (ex. 2026-10-27T08:00:00-04:00).",
                field,
            )
        return timezone.make_aware(value, tz) if timezone.is_naive(value) else value
