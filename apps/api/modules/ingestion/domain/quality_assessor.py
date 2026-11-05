from modules.database.models import Observation
from shared.metrics.metric_catalog import MetricCatalog

from .quality_result import QualityResult

Status = Observation.QualityStatus


class QualityAssessor:
    """Évalue la qualité d'une mesure (logique pure, sans accès aux données).

    Dans l'ordre :

    1. valeur hors limites physiques → invalide ;
    2. horodatage antérieur de plus de 5 min à la mesure précédente → invalide ;
    3. valeur identique depuis ``stuck_after_minutes`` → suspecte ;
    4. variation par minute supérieure à la limite de la zone → suspecte
       (seulement si le contrôle est activé pour la zone).
    """

    DEFAULT_STUCK_AFTER_MINUTES = 15
    MAX_CLOCK_SKEW_SECONDS = 300

    def assess(self, *, metric, value, observed_at, now, history, profile) -> QualityResult:
        """``history`` : mesures précédentes du capteur, la plus récente en premier."""
        definition = MetricCatalog.get(metric)
        plausible_range = definition.plausible_range if definition else None
        if plausible_range and not plausible_range[0] <= value <= plausible_range[1]:
            minimum, maximum = plausible_range
            return QualityResult(Status.INVALID, f"valeur hors limites physiques: {value} (attendu {minimum} à {maximum})")

        previous = self._previous(history, observed_at)
        if previous is None:
            return QualityResult(Status.NORMAL)

        current_time = observed_at or now
        elapsed_seconds = (current_time - previous.moment).total_seconds()
        if elapsed_seconds < -self.MAX_CLOCK_SKEW_SECONDS:
            return QualityResult(Status.INVALID, "horodatage antérieur à la dernière mesure du capteur")

        stuck = self._stuck_minutes(history, value, current_time)
        stuck_after = profile.stuck_after_minutes if profile else self.DEFAULT_STUCK_AFTER_MINUTES
        if stuck is not None and stuck >= stuck_after:
            return QualityResult(Status.SUSPICIOUS, f"valeur inchangée depuis {stuck:.0f} min")

        if not profile or not profile.enabled:
            return QualityResult(Status.NORMAL)

        limit = profile.rate_limits.get(metric)
        minutes = max(elapsed_seconds / 60.0, 1 / 60)
        delta_per_minute = abs(value - previous.value) / minutes
        if limit is not None and delta_per_minute > limit:
            return QualityResult(Status.SUSPICIOUS, f"variation rapide: {delta_per_minute:.2f}/min > {limit:.2f}/min")

        return QualityResult(Status.NORMAL)

    @staticmethod
    def _previous(history, observed_at):
        if observed_at is None:
            return history[0] if history else None
        return next((item for item in history if item.observed_at and item.observed_at < observed_at), None)

    @staticmethod
    def _stuck_minutes(history, value, current_time):
        oldest_unchanged = None
        for item in history:
            if item.value != value:
                break
            oldest_unchanged = item.moment
        if oldest_unchanged is None:
            return None
        return max((current_time - oldest_unchanged).total_seconds() / 60.0, 0)
