import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";
import { isDisplayMetric } from "../constants/metrics";
import type { DisplayMetric } from "../resources/observation";
import type { Zone } from "../resources/zone";

/**
 * Zone et mesure sélectionnées dans l'analyse historique, synchronisées avec
 * l'URL (`?zone=…&metric=…`). Les valeurs absentes ou invalides sont
 * remplacées par la première zone et la première mesure disponibles.
 */
export function useHistoryFilters(zones: Zone[]) {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedZone = searchParams.get("zone");
  const requestedMetric = searchParams.get("metric");

  const zone = useMemo(
    () => zones.find((item) => item.code === requestedZone) ?? zones[0] ?? null,
    [zones, requestedZone],
  );
  const availableMetrics = useMemo(() => (zone?.metrics ?? []).filter(isDisplayMetric), [zone]);
  const metric: DisplayMetric =
    isDisplayMetric(requestedMetric) && availableMetrics.includes(requestedMetric)
      ? requestedMetric
      : (availableMetrics[0] ?? "temperature");

  const update = useCallback(
    (changes: { zone?: string; metric?: DisplayMetric }) =>
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          if (changes.zone) next.set("zone", changes.zone);
          if (changes.metric) next.set("metric", changes.metric);
          next.delete("date");
          return next;
        },
        { replace: true },
      ),
    [setSearchParams],
  );

  return {
    zone,
    metric,
    availableMetrics,
    selectZone: (code: string) => update({ zone: code }),
    selectMetric: (value: DisplayMetric) => update({ metric: value }),
  };
}
