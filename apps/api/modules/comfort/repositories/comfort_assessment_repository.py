from django.db.models import OuterRef, Subquery

from modules.database.models import ComfortAssessment


class ComfortAssessmentRepository:
    """Évaluations de confort enregistrées (lecture seule)."""

    def latest_by_zone(self) -> dict[str, ComfortAssessment]:
        newest = ComfortAssessment.objects.filter(zone=OuterRef("zone")).order_by("-assessed_at", "-id").values("id")[:1]
        assessments = ComfortAssessment.objects.filter(id=Subquery(newest)).select_related("zone")
        return {assessment.zone.code: assessment for assessment in assessments}

    def in_period(self, zone_code, period):
        return (
            ComfortAssessment.objects.filter(
                zone__code=zone_code,
                assessed_at__gte=period.start,
                assessed_at__lt=period.end,
            )
            .order_by("assessed_at")
            .values("assessed_at", "score", "level", "temperature", "humidity")
            .iterator(chunk_size=5000)
        )
