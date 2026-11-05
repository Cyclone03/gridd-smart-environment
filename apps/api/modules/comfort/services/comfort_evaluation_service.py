from django.conf import settings
from django.utils.dateparse import parse_datetime

from modules.database.models import Observation


class ComfortEvaluationService:
    """Évalue le confort d'une zone à chaque mesure de température ou d'humidité.

    La mesure reçue est complétée par la dernière mesure de l'autre facteur
    (au plus ``COMFORT_MAX_INPUT_AGE_MINUTES`` avant). Les mesures invalides
    sont ignorées. L'évaluation est publiée ; le module Database l'enregistre.
    """

    FACTORS = ("temperature", "humidity")

    def __init__(self, *, settings_repository, readings, assessor, producer):
        self._settings = settings_repository
        self._readings = readings
        self._assessor = assessor
        self._producer = producer

    def evaluate(self, observation) -> dict | None:
        metric = observation["type"]
        if metric not in self.FACTORS or observation["quality_status"] == Observation.QualityStatus.INVALID:
            return None
        zone = self._settings.get(observation["zone_code"])
        if zone is None:
            return None

        assessed_at = observation["observed_at"] or observation["received_at"]
        other = next(factor for factor in self.FACTORS if factor != metric)
        values = {
            metric: observation["value"],
            other: self._readings.latest_value(
                zone.zone_code,
                other,
                at=parse_datetime(assessed_at),
                max_age_minutes=settings.COMFORT_MAX_INPUT_AGE_MINUTES,
            ),
        }
        result = self._assessor.assess(zone.profile, values["temperature"], values["humidity"])
        payload = {
            "zone_code": zone.zone_code,
            "observation_id": observation["id"],
            "assessed_at": assessed_at,
            "temperature": result.temperature,
            "humidity": result.humidity,
            "temperature_status": result.temperature_status,
            "humidity_status": result.humidity_status,
            "level": result.level,
            "score": result.score,
        }
        self._producer.assessed(payload)
        return payload
