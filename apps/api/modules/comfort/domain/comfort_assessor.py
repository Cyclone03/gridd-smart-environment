from modules.database.models import ComfortAssessment

from .comfort_result import ComfortResult
from .comfort_status import ComfortStatus

Level = ComfortAssessment.Level


class ComfortAssessor:
    """Confort thermique d'après la température et l'humidité (logique pure).

    Chaque facteur reçoit un état et un score :

    - dans la plage : « ok », 100 ;
    - au plus ``tolerance`` en dehors : léger écart, de 100 à 50 ;
    - au-delà : écart marqué, de 50 à 0 (atteint à deux fois la tolérance).

    Niveau : inconfortable si un facteur est en écart marqué, acceptable s'il y
    a un léger écart, confortable sinon. Score global : moyenne pondérée
    (température 70 %, humidité 30 %) des facteurs disponibles.
    """

    WEIGHTS = {"temperature": 0.7, "humidity": 0.3}

    def assess(self, profile, temperature, humidity) -> ComfortResult:
        temperature_status, temperature_score = self._factor(
            temperature,
            profile.temperature_min,
            profile.temperature_max,
            profile.temperature_tolerance,
            ComfortStatus.TEMPERATURE,
        )
        humidity_status, humidity_score = self._factor(
            humidity,
            profile.humidity_min,
            profile.humidity_max,
            profile.humidity_tolerance,
            ComfortStatus.HUMIDITY,
        )
        return ComfortResult(
            temperature=temperature,
            humidity=humidity,
            temperature_status=temperature_status,
            humidity_status=humidity_status,
            level=self._level(temperature_status, humidity_status),
            score=self._score({"temperature": temperature_score, "humidity": humidity_score}),
        )

    @staticmethod
    def _factor(value, low, high, tolerance, labels):
        if value is None:
            return ComfortStatus.UNKNOWN, None
        if low <= value <= high:
            return ComfortStatus.OK, 100.0
        below = value < low
        distance = low - value if below else value - high
        too_low, slightly_low, slightly_high, too_high = labels
        if distance <= tolerance:
            return (slightly_low if below else slightly_high), 100 - 50 * distance / tolerance
        return (too_low if below else too_high), max(0.0, 50 - 50 * (distance - tolerance) / tolerance)

    @staticmethod
    def _level(*statuses):
        known = [status for status in statuses if status != ComfortStatus.UNKNOWN]
        if not known:
            return Level.UNKNOWN
        if any(ComfortStatus.is_severe(status) for status in known):
            return Level.UNCOMFORTABLE
        if any(status != ComfortStatus.OK for status in known):
            return Level.ACCEPTABLE
        return Level.COMFORTABLE

    def _score(self, scores):
        known = {factor: score for factor, score in scores.items() if score is not None}
        if not known:
            return None
        weight = sum(self.WEIGHTS[factor] for factor in known)
        return round(sum(self.WEIGHTS[factor] * score for factor, score in known.items()) / weight, 1)
