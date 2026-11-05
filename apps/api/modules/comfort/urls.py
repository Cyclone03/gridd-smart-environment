from django.urls import path
from rest_framework.routers import SimpleRouter

from .controllers.comfort_current_controller import ComfortCurrentController
from .controllers.comfort_history_controller import ComfortHistoryController
from .controllers.comfort_profile_controller import ComfortProfileController

router = SimpleRouter()
router.register("comfort/profiles", ComfortProfileController, basename="comfort-profile")

urlpatterns = [
    path("comfort/current/", ComfortCurrentController.as_view(), name="comfort-current"),
    path("comfort/zones/<slug:zone_code>/history/", ComfortHistoryController.as_view(), name="comfort-history"),
    *router.urls,
]
