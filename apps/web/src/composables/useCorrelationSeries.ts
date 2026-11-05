import { CORRELATION_METRICS, type CorrelationMetric } from "../constants/metrics";
import type { ResolvedPeriod } from "../resources/period";
import { getZoneHistory } from "../services/historyService";
import { MIN_POINTS, toSeries, type Series } from "../utils/correlation";
import { useAsyncData } from "./useAsyncData";

/**
 * Séries température / humidité / son d'une zone sur la période appliquée.
 * Seules les mesures disponibles dans la zone et assez fournies (au moins
 * `MIN_POINTS` créneaux) sont retenues.
 */
export function useCorrelationSeries(zoneCode: string | null, metrics: readonly string[], period: ResolvedPeriod) {
  const wanted = CORRELATION_METRICS.filter((metric) => metrics.includes(metric));
  const start = period.start.getTime();
  const end = period.end.getTime();
  return useAsyncData<Series[]>(
    zoneCode && wanted.length >= 2
      ? async (signal) => {
          const histories = await Promise.all(
            wanted.map((metric: CorrelationMetric) =>
              getZoneHistory({ zoneCode, metric, start: new Date(start), end: new Date(end) }, signal).then((history) =>
                toSeries(history, metric),
              ),
            ),
          );
          return histories.filter((series) => series.values.size >= MIN_POINTS);
        }
      : null,
    [zoneCode, wanted.join(","), start, end],
    { keepPrevious: true },
  );
}
