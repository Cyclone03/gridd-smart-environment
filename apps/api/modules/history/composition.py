"""Racine de composition du module History : assemble le cœur avec les
adaptateurs Django. Seul endroit (avec ``apps.py``) qui connaît les deux."""

from django.conf import settings
from django.utils import timezone

from modules.history.adapters.persistence.history_repository import HistoryRepository
from modules.history.core.services.history_service import HistoryService
from shared.kernel.periods import PeriodParser


def history_service() -> HistoryService:
    return HistoryService(
        reader=HistoryRepository(),
        period_parser=PeriodParser(
            max_range_days=settings.HISTORY_MAX_RANGE_DAYS,
            target_points=settings.HISTORY_TARGET_POINTS,
            max_points=settings.HISTORY_MAX_POINTS,
        ),
        timezone_provider=timezone.get_current_timezone,
    )
