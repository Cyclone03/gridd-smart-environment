from django.urls import path
from rest_framework.routers import SimpleRouter

from .controllers.energy_profile_controller import EnergyProfileController
from .controllers.energy_series_controller import EnergySeriesController
from .controllers.energy_summary_controller import EnergySummaryController

router = SimpleRouter()
router.register("energy/profiles", EnergyProfileController, basename="energy-profile")

urlpatterns = [
    path("energy/summary/", EnergySummaryController.as_view(), name="energy-summary"),
    path("energy/zones/<slug:zone_code>/series/", EnergySeriesController.as_view(), name="energy-series"),
    *router.urls,
]
