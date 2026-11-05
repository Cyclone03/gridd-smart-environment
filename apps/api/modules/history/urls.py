from django.urls import path

from .controllers.zone_history_controller import ZoneHistoryController

urlpatterns = [
    path("zones/<slug:zone_code>/history/", ZoneHistoryController.as_view(), name="zone-history"),
]
