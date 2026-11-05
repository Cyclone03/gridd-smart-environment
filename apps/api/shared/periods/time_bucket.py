from django.utils import timezone


class TimeBucket:
    """Créneaux de temps alignés sur l'heure locale."""

    @staticmethod
    def start_of(moment, bucket_minutes, tz):
        """Début du créneau local contenant ``moment`` (minuit pour un jour :
        toutes les granularités proposées divisent exactement 24 h)."""
        local = timezone.localtime(moment, tz)
        minutes = local.hour * 60 + local.minute
        floored = minutes - minutes % bucket_minutes
        return local.replace(hour=floored // 60, minute=floored % 60, second=0, microsecond=0)
