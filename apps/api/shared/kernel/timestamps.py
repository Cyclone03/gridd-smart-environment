"""Horodatages sans dépendance à Django (équivalents purs de ``django.utils``)."""

import re
from datetime import datetime, timedelta, timezone

# Une date seule (« 2026-10-27 ») n'est pas une date et heure, comme pour
# ``django.utils.dateparse.parse_datetime``.
_DATE_ONLY = re.compile(r"\d{4}-?\d{2}-?\d{2}")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value) -> datetime | None:
    """Date et heure ISO 8601 ou ``None`` si la chaîne n'en est pas une."""
    if not isinstance(value, str) or not value.strip() or _DATE_ONLY.fullmatch(value.strip()):
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        return None


def is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None


def make_aware(value: datetime, tz) -> datetime:
    """Associe le fuseau ``tz`` (``zoneinfo``) à une date naïve."""
    return value if is_aware(value) else value.replace(tzinfo=tz)


def is_utc(value: datetime) -> bool:
    return is_aware(value) and value.utcoffset() == timedelta(0)
