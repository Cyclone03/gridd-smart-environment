from shared.periods import TimeBucket


class EnergyAggregator:
    """Totaux et séries d'énergie à partir des intervalles estimés (logique pure).

    Un intervalle est rattaché au créneau qui contient sa fin.
    """

    USES = ("lighting", "equipment", "heating", "cooling", "total")

    def totals(self, rows) -> dict:
        sums = {use: 0.0 for use in self.USES}
        seconds = 0.0
        for row in rows:
            for use in self.USES:
                sums[use] += row[f"{use}_wh"]
            seconds += row["duration_seconds"]
        hours = seconds / 3600
        return {
            **{f"{use}_kwh": round(sums[use] / 1000, 3) for use in self.USES},
            "covered_hours": round(hours, 2),
            "average_power_w": round(sums["total"] / hours, 1) if hours else None,
        }

    def by_zone(self, rows) -> dict[str, dict]:
        grouped = {}
        for row in rows:
            grouped.setdefault(row["zone__code"], []).append(row)
        return {zone_code: self.totals(zone_rows) for zone_code, zone_rows in grouped.items()}

    def series(self, rows, bucket_minutes, tz) -> list[dict]:
        buckets = {}
        for row in rows:
            start = TimeBucket.start_of(row["end"], bucket_minutes, tz)
            bucket = buckets.setdefault(start, {use: 0.0 for use in self.USES})
            for use in self.USES:
                bucket[use] += row[f"{use}_wh"]
        return [
            {"time": start.isoformat(), **{f"{use}_kwh": round(bucket[use] / 1000, 4) for use in self.USES}}
            for start, bucket in sorted(buckets.items())
        ]
