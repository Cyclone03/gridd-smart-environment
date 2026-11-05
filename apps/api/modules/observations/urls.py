from django.urls import path
from rest_framework.routers import SimpleRouter

from .controllers.observation_controller import ObservationController
from .controllers.sensor_controller import SensorController
from .controllers.zone_controller import ZoneController
from .controllers.zone_latest_controller import ZoneLatestController

router = SimpleRouter()
router.register("zones", ZoneController, basename="zone")
router.register("sensors", SensorController, basename="sensor")
router.register("observations", ObservationController, basename="observation")

urlpatterns = [
    path("zones/<slug:zone_code>/latest/", ZoneLatestController.as_view(), name="latest-by-zone"),
    *router.urls,
]
