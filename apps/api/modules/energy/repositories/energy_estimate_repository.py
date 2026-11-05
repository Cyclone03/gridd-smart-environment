from modules.database.models import EnergyEstimate


class EnergyEstimateRepository:
    """Intervalles d'énergie estimés (lecture seule)."""

    FIELDS = (
        "zone__code",
        "end",
        "duration_seconds",
        "lighting_wh",
        "equipment_wh",
        "heating_wh",
        "cooling_wh",
        "total_wh",
    )

    def in_period(self, period, zone_code=None):
        """Intervalles dont la fin est dans ``[start ; end[``, triés chronologiquement."""
        estimates = EnergyEstimate.objects.filter(end__gte=period.start, end__lt=period.end, zone__active=True)
        if zone_code:
            estimates = estimates.filter(zone__code=zone_code)
        return list(estimates.order_by("end").values(*self.FIELDS))
