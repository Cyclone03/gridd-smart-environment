from django.utils import timezone

from modules.database.models import Observation
from modules.history.domain.bucket_aggregator import BucketAggregator
from modules.history.domain.history_statistics import HistoryStatistics
from modules.history.repositories.history_repository import HistoryRepository
from shared.metrics.metric_catalog import MetricCatalog
from shared.periods import PeriodParamError, PeriodParser


class HistoryService:
    """Historique agrégé d'une mesure pour une zone sur une période."""

    def __init__(self, repository=None, aggregator=None, statistics=None):
        self._repository = repository or HistoryRepository()
        self._aggregator = aggregator or BucketAggregator(Observation.QualityStatus.NORMAL)
        self._statistics = statistics or HistoryStatistics()

    def history(self, zone_code, params) -> dict | None:
        """Retourne ``None`` si la zone est inconnue ; lève ``PeriodParamError``
        pour un paramètre invalide."""
        zone = self._repository.active_zone(zone_code)
        if zone is None:
            return None
        metric = params.get("type", "temperature")
        definition = MetricCatalog.get(metric)
        if definition is None:
            raise PeriodParamError("Type de mesure invalide.", "type", "Type de mesure inconnu.")

        tz = timezone.get_current_timezone()
        period = PeriodParser.from_settings().parse(params, tz=tz)
        points, values = self._aggregator.aggregate(
            self._repository.rows(zone, metric, period), period.bucket_minutes, tz
        )
        return {
            "zone_code": zone.code,
            "type": metric,
            "start": timezone.localtime(period.start, tz).isoformat(),
            "end": timezone.localtime(period.end, tz).isoformat(),
            "timezone": str(tz),
            "hours": period.hours,
            "date": period.date,
            "bucket_minutes": period.bucket_minutes,
            "unit": definition.unit,
            "points": points,
            "statistics": self._statistics.summarize(points, values, definition.trend_tolerance),
        }
