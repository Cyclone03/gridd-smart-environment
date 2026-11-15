import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { DEFAULT_PERIOD, LIVE_WINDOW_TICK_MS } from "../constants/periods";
import type { ObservationPeriod, ResolvedPeriod } from "../resources/period";
import { periodFromSearchParams, periodToSearchParams, resolvePeriod, samePeriod } from "../utils/period";

/**
 * Période d'observation appliquée aux graphiques d'une vue.
 *
 * - la période appliquée est synchronisée avec l'URL (`?period=` ou
 *   `?start=&end=`), ce qui permet de partager ou recharger la vue ;
 * - `resolved` : bornes envoyées à l'API. Elles ne changent que si la
 *   période change ou sur demande (`refresh()`) : un seul chargement HTTP ;
 * - `window` : bornes affichées. Pour une période glissante (« dernière
 *   heure »…), elles suivent l'heure courante localement ; les nouvelles
 *   mesures arrivent par le WebSocket, sans nouvelle requête.
 */
export function useObservationPeriod(fallback: ObservationPeriod = DEFAULT_PERIOD) {
  const [searchParams, setSearchParams] = useSearchParams();
  const period = useMemo(() => periodFromSearchParams(searchParams, fallback), [searchParams, fallback]);
  const periodKey = period.kind === "preset" ? period.preset : `${period.start}|${period.end}`;
  const [reloadKey, setReloadKey] = useState(0);
  const [now, setNow] = useState(() => Date.now());

  // `reloadKey` force un nouveau calcul de « maintenant » pour la même période.
  const resolved: ResolvedPeriod = useMemo(() => resolvePeriod(period, new Date()), [periodKey, reloadKey]);

  useEffect(() => {
    if (!resolved.live) return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), LIVE_WINDOW_TICK_MS);
    return () => window.clearInterval(timer);
  }, [resolved.live, periodKey, reloadKey]);

  const window_: ResolvedPeriod = useMemo(
    () => (resolved.live ? resolvePeriod(period, new Date(Math.max(now, resolved.end.getTime()))) : resolved),
    [resolved, now, periodKey],
  );

  const refresh = useCallback(() => setReloadKey((value) => value + 1), []);

  const apply = useCallback(
    (next: ObservationPeriod) => {
      // Réappliquer la même période équivaut à une actualisation.
      if (samePeriod(next, period)) refresh();
      else setSearchParams((current) => periodToSearchParams(next, current), { replace: true });
    },
    [period, refresh, setSearchParams],
  );

  return { period, resolved, window: window_, apply, refresh };
}
