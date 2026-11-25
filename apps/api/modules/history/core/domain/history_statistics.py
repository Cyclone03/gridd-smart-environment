class HistoryStatistics:
    """Statistiques d'une série : minimum, maximum, moyenne, nombre, tendance."""

    @staticmethod
    def trend(points, tolerance) -> str:
        """Compare le premier et le dernier créneau à une tolérance propre à la mesure."""
        if len(points) < 2:
            return "stable"
        delta = points[-1]["average"] - points[0]["average"]
        if delta > tolerance:
            return "rising"
        if delta < -tolerance:
            return "falling"
        return "stable"

    def summarize(self, points, values, tolerance) -> dict:
        return {
            "minimum": min(values) if values else None,
            "maximum": max(values) if values else None,
            "average": round(sum(values) / len(values), 2) if values else None,
            "count": len(values),
            "trend": self.trend(points, tolerance),
        }
