import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { DEFAULT_PERIOD, LIVE_PERIOD_REFRESH_MS } from "../constants/periods";
import type { ObservationPeriod, ResolvedPeriod } from "../resources/period";
import { periodFromSearchParams, periodToSearchParams, resolvePeriod, samePeriod } from "../utils/period";

/**
 * Période d'observation appliquée aux graphiques d'une vue.
 *
 * - la période appliquée est synchronisée avec l'URL (`?period=` ou
 *   `?start=&end=`), ce qui permet de partager ou recharger la vue ;
 * - les bornes sont recalculées uniquement quand la période change, à chaque
 *   `LIVE_PERIOD_REFRESH_MS` pour une période glissante (« dernière heure »…),
 *   ou sur demande avec `refresh()` : chaque recalcul déclenche un seul
 *   rechargement des graphiques.
 */
export function useObservationPeriod(fallback: ObservationPeriod = DEFAULT_PERIOD) {
  const [searchParams, setSearchParams] = useSearchParams();
  const period = useMemo(() => periodFromSearchParams(searchParams, fallback), [searchParams, fallback]);
  const periodKey = period.kind === "preset" ? period.preset : `${period.start}|${period.end}`;
  const [tick, setTick] = useState(0);

  // `tick` force un nouveau calcul de « maintenant » pour la même période.
  const resolved: ResolvedPeriod = useMemo(() => resolvePeriod(period, new Date()), [periodKey, tick]);

  useEffect(() => {
    if (!resolved.live) return;
    const timer = window.setInterval(() => setTick((value) => value + 1), LIVE_PERIOD_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [resolved.live, periodKey]);

  const refresh = useCallback(() => setTick((value) => value + 1), []);

  const apply = useCallback(
    (next: ObservationPeriod) => {
      // Réappliquer la même période équivaut à une actualisation.
      if (samePeriod(next, period)) refresh();
      else setSearchParams((current) => periodToSearchParams(next, current), { replace: true });
    },
    [period, refresh, setSearchParams],
  );

  return { period, resolved, apply, refresh };
}
