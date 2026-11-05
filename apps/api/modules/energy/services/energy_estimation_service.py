from django.conf import settings
from django.utils.dateparse import parse_datetime

from modules.database.models import Observation


class EnergyEstimationService:
    """Estime l'énergie consommée par une zone entre deux mesures.

    Chaque mesure valide de température ou d'occupation clôt l'intervalle
    ouvert par la mesure précédente de la zone. La puissance de l'intervalle
    est calculée avec les valeurs connues à son début (température,
    occupation mesurée ou, à défaut, occupation par défaut de la zone).

    Ne sont pas estimés : la première mesure d'une zone, un intervalle plus
    long que ``ENERGY_MAX_INTERVAL_MINUTES`` (capteur muet), une mesure
    arrivée en retard (une mesure plus récente existe déjà) et une mesure
    simultanée à une autre déjà enregistrée (température et occupation
    envoyées au même instant ne ferment qu'un seul intervalle).
    """

    INPUTS = ("temperature", "occupancy")

    def __init__(self, *, settings_repository, inputs, model, producer):
        self._settings = settings_repository
        self._inputs = inputs
        self._model = model
        self._producer = producer

    def estimate(self, observation) -> dict | None:
        if observation["type"] not in self.INPUTS or observation["quality_status"] == Observation.QualityStatus.INVALID:
            return None
        zone = self._settings.get(observation["zone_code"])
        if zone is None:
            return None

        end = parse_datetime(observation["observed_at"] or observation["received_at"])
        if self._inputs.has_later(zone.zone_code, after=end, exclude_id=observation["id"]):
            return None
        if self._inputs.has_simultaneous_before(zone.zone_code, moment=end, observation_id=observation["id"]):
            return None
        start = self._inputs.previous_moment(zone.zone_code, before=end, exclude_id=observation["id"])
        if start is None:
            return None
        duration = (end - start).total_seconds()
        if duration <= 0 or duration > settings.ENERGY_MAX_INTERVAL_MINUTES * 60:
            return None

        profile = zone.profile
        temperature = self._latest(zone.zone_code, "temperature", start)
        measured_occupancy = self._latest(zone.zone_code, "occupancy", start)
        occupancy = measured_occupancy if measured_occupancy is not None else profile.default_occupancy
        power = self._model.power(profile, temperature, occupancy)

        payload = {
            "zone_code": zone.zone_code,
            "observation_id": observation["id"],
            "start": start.isoformat(),
            "end": end.isoformat(),
            "duration_seconds": duration,
            "indoor_temperature": temperature,
            "occupancy": occupancy,
            "occupancy_source": "sensor" if measured_occupancy is not None else "profile",
            "hvac_estimated": power.hvac_estimated,
            **power.energy_wh(duration),
        }
        self._producer.estimated(payload)
        return payload

    def _latest(self, zone_code, metric, at):
        return self._inputs.latest_value(zone_code, metric, at=at, max_age_minutes=settings.ENERGY_MAX_INPUT_AGE_MINUTES)
