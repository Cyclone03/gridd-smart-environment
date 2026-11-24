import unittest

from ai_prediction_service.config import ServiceSettings


class ServiceSettingsTests(unittest.TestCase):
    def test_reads_coordinates_and_timeout_from_environment(self):
        settings = ServiceSettings.from_env(
            {
                "GRIDD_API_BASE_URL": "http://gridd.test/",
                "OPEN_METEO_LATITUDE": "45.5",
                "OPEN_METEO_LONGITUDE": "-73.6",
                "HTTP_TIMEOUT_SECONDS": "3.5",
            }
        )

        self.assertEqual(settings.gridd_api_base_url, "http://gridd.test")
        self.assertEqual(settings.open_meteo_latitude, 45.5)
        self.assertEqual(settings.open_meteo_longitude, -73.6)
        self.assertEqual(settings.http_timeout_seconds, 3.5)

    def test_coordinates_are_required(self):
        with self.assertRaisesRegex(ValueError, "OPEN_METEO_LATITUDE"):
            ServiceSettings.from_env({})

    def test_coordinate_ranges_are_validated(self):
        with self.assertRaisesRegex(ValueError, "between -90 and 90"):
            ServiceSettings.from_env(
                {"OPEN_METEO_LATITUDE": "91", "OPEN_METEO_LONGITUDE": "-73.6"}
            )


if __name__ == "__main__":
    unittest.main()
