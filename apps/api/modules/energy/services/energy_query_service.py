from django.utils import timezone

from modules.energy.domain.energy_aggregator import EnergyAggregator
from modules.energy.repositories.energy_estimate_repository import EnergyEstimateRepository
from modules.energy.repositories.energy_settings_repository import EnergySettingsRepository
from shared.periods import PeriodParser


class EnergyQueryService:
    """Consultation des estimations : bilan par zone et série d'une zone."""

    def __init__(self, settings_repository=None, estimates=None, aggregator=None):
        self._settings = settings_repository or EnergySettingsRepository()
        self._estimates = estimates or EnergyEstimateRepository()
        self._aggregator = aggregator or EnergyAggregator()

    def summary(self, params) -> dict:
        tz = timezone.get_current_timezone()
        period = PeriodParser.from_settings().parse(params, tz=tz)
        rows = self._estimates.in_period(period)
        by_zone = self._aggregator.by_zone(rows)
        empty = self._aggregator.totals([])
        return {
            **self._period(period, tz),
            "total": self._aggregator.totals(rows),
            "zones": [
                {
                    "zone_code": zone.zone_code,
                    "zone_name": zone.zone_name,
                    "zone_type": zone.zone_type,
                    "customized": zone.customized,
                    **by_zone.get(zone.zone_code, empty),
                }
                for zone in self._settings.all()
            ],
        }

    def series(self, zone_code, params) -> dict | None:
        zone = self._settings.get(zone_code)
        if zone is None:
            return None
        tz = timezone.get_current_timezone()
        period = PeriodParser.from_settings().parse(params, tz=tz)
        rows = self._estimates.in_period(period, zone_code)
        return {
            "zone_code": zone.zone_code,
            **self._period(period, tz),
            "bucket_minutes": period.bucket_minutes,
            "points": self._aggregator.series(rows, period.bucket_minutes, tz),
            "total": self._aggregator.totals(rows),
        }

    @staticmethod
    def _period(period, tz):
        return {
            "start": timezone.localtime(period.start, tz).isoformat(),
            "end": timezone.localtime(period.end, tz).isoformat(),
        }
