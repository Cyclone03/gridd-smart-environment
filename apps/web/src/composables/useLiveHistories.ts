import { useEffect, useMemo, useRef, useState } from "react";
import { TREND_TOLERANCES } from "../constants/metrics";
import { errorMessage } from "../requests/httpClient";
import type { ZoneHistory } from "../resources/history";
import type { MetricType, Observation } from "../resources/observation";
import type { ResolvedPeriod } from "../resources/period";
import { getZoneHistory } from "../services/historyService";
import { useDashboard } from "../stores/dashboardStore";
import { mergeObservations, trimHistory } from "../utils/history";
import { useAsyncData } from "./useAsyncData";

type Histories = Partial<Record<MetricType, ZoneHistory>>;
type Errors = Partial<Record<MetricType, string>>;

interface Loaded {
  histories: Histories;
  errors: Errors;
}

/** Mesures reçues pendant un chargement, conservées au plus (évite une fuite). */
const MAX_BUFFERED = 5_000;

function mergeAll(histories: Histories, observations: Observation[], until: number): Histories {
  let changed = false;
  const next: Histories = {};
  for (const [metric, history] of Object.entries(histories) as [MetricType, ZoneHistory][]) {
    const merged = mergeObservations(history, observations, TREND_TOLERANCES[metric], until);
    changed ||= merged !== history;
    next[metric] = merged;
  }
  return changed ? next : histories;
}

/**
 * Historiques agrégés d'une zone pour plusieurs mesures, tenus à jour en direct.
 *
 * - un seul chargement HTTP par sélection (zone, mesures, période) : c'est une
 *   requête d'analyse paramétrée, pas un rafraîchissement périodique ;
 * - ensuite, les mesures reçues par le WebSocket sont ajoutées aux créneaux
 *   (statistiques recalculées) et, pour une période glissante, les créneaux
 *   sortis de la fenêtre affichée (`shown`) sont retirés. Aucune requête n'est refaite.
 *
 * Chaque mesure a son propre état d'erreur : l'échec d'une mesure n'empêche
 * pas d'afficher les autres.
 */
export function useLiveHistories(
  zoneCode: string | null,
  metrics: readonly MetricType[],
  period: ResolvedPeriod,
  shown: ResolvedPeriod,
) {
  const { subscribeObservations } = useDashboard();
  const metricsKey = metrics.join(",");
  const start = period.start.getTime();
  const end = period.end.getTime();

  const base = useAsyncData<Loaded>(
    zoneCode && metrics.length
      ? async (signal) => {
          const results = await Promise.allSettled(
            metrics.map((metric) =>
              getZoneHistory({ zoneCode, metric, start: new Date(start), end: new Date(end) }, signal),
            ),
          );
          const loaded: Loaded = { histories: {}, errors: {} };
          results.forEach((result, index) => {
            if (result.status === "fulfilled") loaded.histories[metrics[index]] = result.value;
            else loaded.errors[metrics[index]] = errorMessage(result.reason, "Chargement impossible.");
          });
          // Tout a échoué (réseau, annulation…) : erreur globale.
          if (!Object.keys(loaded.histories).length) throw (results[0] as PromiseRejectedResult).reason;
          return loaded;
        }
      : null,
    [zoneCode, metricsKey, start, end],
    // Pendant un rechargement, les anciennes courbes restent affichées.
    { keepPrevious: true },
  );

  // Mesures reçues depuis le début du chargement : appliquées à son arrivée.
  const buffer = useRef<Observation[]>([]);
  useEffect(() => {
    buffer.current = [];
  }, [zoneCode, metricsKey, start, end]);

  // Fin acceptée pour une période fixe ; illimitée pour une période glissante.
  const until = period.live ? Number.POSITIVE_INFINITY : end;
  const acceptsLive = period.live || end > Date.now();

  const [histories, setHistories] = useState<Histories | null>(null);
  useEffect(() => {
    if (!base.data) {
      setHistories(null);
      return;
    }
    setHistories(acceptsLive ? mergeAll(base.data.histories, buffer.current, until) : base.data.histories);
  }, [base.data]);

  useEffect(() => {
    if (!zoneCode || !acceptsLive) return;
    return subscribeObservations((batch) => {
      const relevant = batch.filter(
        (observation) => observation.zone_code === zoneCode && metrics.includes(observation.type),
      );
      if (!relevant.length) return;
      buffer.current = [...buffer.current, ...relevant].slice(-MAX_BUFFERED);
      setHistories((current) => (current ? mergeAll(current, relevant, until) : current));
    });
  }, [zoneCode, metricsKey, acceptsLive, until, subscribeObservations]);

  // Fenêtre glissante : les créneaux trop anciens sortent du graphique.
  const windowStart = shown.start.getTime();
  const visible = useMemo(() => {
    if (!histories || !period.live) return histories;
    const next: Histories = {};
    for (const [metric, history] of Object.entries(histories) as [MetricType, ZoneHistory][])
      next[metric] = trimHistory(history, windowStart, TREND_TOLERANCES[metric]);
    return next;
  }, [histories, windowStart, period.live]);

  return {
    histories: visible ?? {},
    errors: base.data?.errors ?? {},
    loading: base.loading,
    error: base.error,
    reload: base.reload,
  };
}
