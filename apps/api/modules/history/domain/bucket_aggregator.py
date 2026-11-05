from shared.periods import TimeBucket


class BucketAggregator:
    """Regroupe des mesures en créneaux alignés sur l'heure locale."""

    def __init__(self, normal_status="normal"):
        self._normal_status = normal_status

    def aggregate(self, rows, bucket_minutes, tz):
        """``rows`` : ``{value, observed_at, received_at, quality_status}``.

        Retourne les points (moyenne, min, max, nombre, mesures suspectes)
        triés chronologiquement et la liste de toutes les valeurs.
        """
        buckets = {}
        values = []
        for row in rows:
            start = TimeBucket.start_of(row["observed_at"] or row["received_at"], bucket_minutes, tz)
            bucket = buckets.setdefault(start, {"values": [], "suspicious": 0})
            value = float(row["value"])
            bucket["values"].append(value)
            values.append(value)
            if row["quality_status"] != self._normal_status:
                bucket["suspicious"] += 1

        points = [
            {
                "time": start.isoformat(),
                "average": round(sum(bucket["values"]) / len(bucket["values"]), 2),
                "minimum": min(bucket["values"]),
                "maximum": max(bucket["values"]),
                "count": len(bucket["values"]),
                "suspicious_count": bucket["suspicious"],
            }
            for start, bucket in sorted(buckets.items())
        ]
        return points, values
