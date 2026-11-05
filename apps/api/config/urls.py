"""Routage HTTP : point d'entrée unique qui assemble les routes des modules.

Chaque module expose ses propres routes (``modules/<module>/urls.py``) ;
aucune route n'est définie ici. L'interface est une application séparée
(``web/``) : le backend n'expose que l'API, l'admin Django et les WebSocket
(voir ``config/asgi.py``).
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("modules.health.urls")),
    path("api/", include("modules.history.urls")),
    path("api/", include("modules.observations.urls")),
    path("api/", include("modules.alarms.urls")),
    path("api/", include("modules.comfort.urls")),
    path("api/", include("modules.energy.urls")),
]
