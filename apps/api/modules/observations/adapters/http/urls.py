from django.urls import path
from rest_framework.routers import SimpleRouter

from .climate_prediction_controller import ClimatePredictionController
from .observation_controller import ObservationController
from .sensor_controller import SensorController
from .weather_snapshot_controller import WeatherSnapshotController
from .zone_controller import ZoneController
from .zone_latest_controller import ZoneLatestController

router = SimpleRouter()
router.register("zones", ZoneController, basename="zone")
router.register("sensors", SensorController, basename="sensor")
router.register("observations", ObservationController, basename="observation")

urlpatterns = [
    path("climate-predictions/latest/", ClimatePredictionController.as_view(), name="latest-climate-predictions"),
    path("weather/latest/", WeatherSnapshotController.as_view(), name="latest-weather-snapshot"),
    path("zones/<slug:zone_code>/latest/", ZoneLatestController.as_view(), name="latest-by-zone"),
    *router.urls,
]
