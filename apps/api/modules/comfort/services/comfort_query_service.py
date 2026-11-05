from django.utils import timezone

from modules.comfort.domain.comfort_history_aggregator import ComfortHistoryAggregator
from modules.comfort.repositories.comfort_assessment_repository import ComfortAssessmentRepository
from modules.comfort.repositories.comfort_settings_repository import ComfortSettingsRepository
from shared.periods import PeriodParser


class ComfortQueryService:
    """Consultation du confort : état actuel des zones et historique."""

    def __init__(self, settings_repository=None, assessments=None, aggregator=None):
        self._settings = settings_repository or ComfortSettingsRepository()
        self._assessments = assessments or ComfortAssessmentRepository()
        self._aggregator = aggregator or ComfortHistoryAggregator()

    def current(self) -> list[dict]:
        """Chaque zone active, ses plages de confort et sa dernière évaluation."""
        latest = self._assessments.latest_by_zone()
        return [{"settings": zone, "assessment": latest.get(zone.zone_code)} for zone in self._settings.all()]

    def history(self, zone_code, params) -> dict | None:
        zone = self._settings.get(zone_code)
        if zone is None:
            return None
        tz = timezone.get_current_timezone()
        period = PeriodParser.from_settings().parse(params, tz=tz)
        points, summary = self._aggregator.aggregate(
            self._assessments.in_period(zone_code, period), period.bucket_minutes, tz
        )
        return {
            "zone_code": zone.zone_code,
            "start": timezone.localtime(period.start, tz).isoformat(),
            "end": timezone.localtime(period.end, tz).isoformat(),
            "bucket_minutes": period.bucket_minutes,
            "profile": zone.profile.to_dict(),
            "points": points,
            "summary": summary,
        }
