import type { MetricType } from "../resources/observation";
import type { ResolvedPeriod } from "../resources/period";
import { getZoneHistory } from "../services/historyService";
import { useAsyncData } from "./useAsyncData";

/** Historique d'une mesure pour la zone et la période appliquée. */
export function useZoneHistory(zoneCode: string | null, metric: MetricType, period: ResolvedPeriod) {
  const start = period.start.getTime();
  const end = period.end.getTime();
  return useAsyncData(
    zoneCode
      ? (signal) => getZoneHistory({ zoneCode, metric, start: new Date(start), end: new Date(end) }, signal)
      : null,
    [zoneCode, metric, start, end],
    // Pendant une actualisation, l'ancien graphique reste affiché.
    { keepPrevious: true },
  );
}
