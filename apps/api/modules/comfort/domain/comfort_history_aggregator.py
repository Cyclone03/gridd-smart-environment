from shared.periods import TimeBucket


class ComfortHistoryAggregator:
    """Regroupe les évaluations de confort par créneau (logique pure).

    Les proportions sont calculées sur le nombre d'évaluations (une par
    mesure de température ou d'humidité), hors évaluations indéterminées.
    """

    LEVELS = ("comfortable", "acceptable", "uncomfortable")

    def aggregate(self, rows, bucket_minutes, tz):
        buckets = {}
        for row in rows:
            start = TimeBucket.start_of(row["assessed_at"], bucket_minutes, tz)
            bucket = buckets.setdefault(
                start, {"scores": [], "temperatures": [], "humidities": [], **{level: 0 for level in self.LEVELS}}
            )
            if row["level"] in self.LEVELS:
                bucket[row["level"]] += 1
            for key, field in (("scores", "score"), ("temperatures", "temperature"), ("humidities", "humidity")):
                if row[field] is not None:
                    bucket[key].append(row[field])

        points = [
            {
                "time": start.isoformat(),
                "score": self._mean(bucket["scores"]),
                "temperature": self._mean(bucket["temperatures"]),
                "humidity": self._mean(bucket["humidities"]),
                **{level: bucket[level] for level in self.LEVELS},
            }
            for start, bucket in sorted(buckets.items())
        ]
        return points, self._summary(buckets.values())

    def _summary(self, buckets):
        counts = {level: sum(bucket[level] for bucket in buckets) for level in self.LEVELS}
        total = sum(counts.values())
        scores = [score for bucket in buckets for score in bucket["scores"]]
        return {
            "count": total,
            "average_score": self._mean(scores),
            **{f"{level}_ratio": round(counts[level] / total, 3) if total else None for level in self.LEVELS},
        }

    @staticmethod
    def _mean(values):
        return round(sum(values) / len(values), 1) if values else None
