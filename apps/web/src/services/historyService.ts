import { request } from "../requests/httpClient";
import type { HistoryQuery, ZoneHistory } from "../resources/history";

/**
 * Historique agrégé d'une mesure sur une période arbitraire.
 * Les bornes sont transmises en ISO 8601 (UTC) ; le backend valide la
 * période, choisit la granularité et répond dans le fuseau du serveur.
 */
export function getZoneHistory(query: HistoryQuery, signal?: AbortSignal) {
  return request<ZoneHistory>(`/api/zones/${encodeURIComponent(query.zoneCode)}/history/`, {
    query: {
      type: query.metric,
      start: query.start,
      end: query.end,
      bucket_minutes: query.bucketMinutes,
    },
    signal,
  });
}
