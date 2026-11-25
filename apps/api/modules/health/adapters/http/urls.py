from django.urls import path

from .health_controller import HealthController

urlpatterns = [
    path("health/", HealthController.as_view(), name="health"),
]
