from django.test import SimpleTestCase, override_settings

from modules.ia import composition
from modules.ia.adapters.http.gridd_api_observation_source import GriddApiObservationSource
from modules.ia.adapters.persistence.database_observation_source import DatabaseObservationSource


class CompositionTests(SimpleTestCase):
    def test_observation_source_is_chosen_by_settings(self):
        self.assertIsInstance(composition.observation_source(), DatabaseObservationSource)
        with override_settings(AI_OBSERVATION_SOURCE="api", GRIDD_API_BASE_URL="http://api:8000"):
            self.assertIsInstance(composition.observation_source(), GriddApiObservationSource)
        with override_settings(AI_OBSERVATION_SOURCE="ftp"), self.assertRaises(ValueError):
            composition.observation_source()

    def test_weather_coordinates_are_required(self):
        with override_settings(OPEN_METEO_LATITUDE=None, OPEN_METEO_LONGITUDE=-73.6), self.assertRaises(ValueError):
            composition.weather_source()
        with override_settings(OPEN_METEO_LATITUDE=45.5, OPEN_METEO_LONGITUDE=-73.6):
            self.assertIsNotNone(composition.weather_source())

    def test_bundled_manifest_is_valid(self):
        with override_settings(OPEN_METEO_LATITUDE=45.5, OPEN_METEO_LONGITUDE=-73.6):
            cycle = composition.prediction_cycle()
        self.assertIsNotNone(cycle)
