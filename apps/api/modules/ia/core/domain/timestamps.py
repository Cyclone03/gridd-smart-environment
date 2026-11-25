from datetime import datetime, timezone

from modules.ia.core.errors import TimestampFormatError


def parse_utc_timestamp(
    value: object,
    field: str,
    *,
    optional: bool = False,
    assume_utc: bool = False,
) -> datetime | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value:
        raise TimestampFormatError(f"{field} must be a non-empty ISO 8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TimestampFormatError(f"{field} is not a valid ISO 8601 timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        if not assume_utc:
            raise TimestampFormatError(f"{field} must include a UTC offset.")
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
