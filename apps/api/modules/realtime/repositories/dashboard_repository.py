from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone

from modules.database.models import Alert, Observation, Sensor, Zone
from shared.metrics.metric_catalog import MetricCatalog


class DashboardRepository:
    """Lecture (seule) des données affichées par les tableaux de bord temps réel."""

    def zones(self):
        """Zones actives triées par nom, avec leurs capteurs actifs et leur profil."""
        return list(
            Zone.objects.filter(active=True)
            .select_related("threshold_profile")
            .prefetch_related(
                Prefetch("sensors", queryset=Sensor.objects.filter(active=True), to_attr="active_sensors")
            )
            .order_by("name")
        )

    def latest_observations(self, zones):
        """Dernière observation de chaque zone et de chaque type de mesure.

        Une requête par couple (zone, type) via l'index ``zone, type, -observed_at`` :
        un capteur très bavard ne masque pas une mesure moins fréquente.
        Pas de ``NULLS LAST`` : sous PostgreSQL ce tri n'utilise pas l'index et
        lisait toutes les mesures de la zone (≈ 5 s par requête, instantané
        WebSocket au-delà de 15 s).
        """
        latest = []
        for zone in zones:
            for metric in MetricCatalog.keys():
                observations = Observation.objects.filter(zone=zone, type=metric).select_related("zone", "sensor")
                observation = observations.filter(observed_at__isnull=False).order_by("-observed_at").first()
                if observation is None:
                    observation = observations.filter(observed_at__isnull=True).order_by("-pk").first()
                if observation is not None:
                    latest.append(observation)
        return sorted(latest, key=lambda item: item.observed_at or item.received_at, reverse=True)

    def active_alerts(self, limit):
        return list(
            Alert.objects.filter(active=True).select_related("zone", "rule").order_by("-created_at")[:limit]
        )

    def resolved_alerts(self, *, days, limit):
        since = timezone.now() - timedelta(days=days)
        return list(
            Alert.objects.filter(active=False, created_at__gte=since)
            .select_related("zone", "rule")
            .order_by("-created_at")[:limit]
        )
