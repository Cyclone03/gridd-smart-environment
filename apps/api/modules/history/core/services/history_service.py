from datetime import timezone

from modules.history.core.domain.bucket_aggregator import BucketAggregator
from modules.history.core.domain.history_statistics import HistoryStatistics
from shared.kernel.metrics import MetricCatalog
from shared.kernel.periods import PeriodParamError


class HistoryService:
    """Historique agrégé d'une mesure pour une zone sur une période.

    Dépendances injectées : ``reader`` (port ``HistoryReader``), ``period_parser``
    (``PeriodParser`` configuré par l'hôte) et ``timezone_provider`` (fuseau
    d'affichage, UTC par défaut).
    """

    def __init__(self, *, reader, period_parser, timezone_provider=None, aggregator=None, statistics=None):
        self._reader = reader
        self._period_parser = period_parser
        self._timezone_provider = timezone_provider or (lambda: timezone.utc)
        self._aggregator = aggregator or BucketAggregator()
        self._statistics = statistics or HistoryStatistics()

    def history(self, zone_code, params) -> dict | None:
        """Retourne ``None`` si la zone est inconnue ; lève ``PeriodParamError``
        pour un paramètre invalide."""
        zone = self._reader.active_zone(zone_code)
        if zone is None:
            return None
        metric = params.get("type", "temperature")
        definition = MetricCatalog.get(metric)
        if definition is None:
            raise PeriodParamError("Type de mesure invalide.", "type", "Type de mesure inconnu.")

        tz = self._timezone_provider()
        period = self._period_parser.parse(params, tz=tz)
        points, values = self._aggregator.aggregate(
            self._reader.rows(zone, metric, period), period.bucket_minutes, tz
        )
        return {
            "zone_code": zone.code,
            "type": metric,
            "start": period.start.astimezone(tz).isoformat(),
            "end": period.end.astimezone(tz).isoformat(),
            "timezone": str(tz),
            "hours": period.hours,
            "date": period.date,
            "bucket_minutes": period.bucket_minutes,
            "unit": definition.unit,
            "points": points,
            "statistics": self._statistics.summarize(points, values, definition.trend_tolerance),
        }
