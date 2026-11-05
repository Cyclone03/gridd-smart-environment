import { request } from "../requests/httpClient";
import type { ComfortHistory, ComfortProfile, ZoneComfort } from "../resources/comfort";
import { chartBucketMinutes } from "../utils/period";

const BASE = "/api/comfort/";

/** Confort actuel de chaque zone, avec ses plages applicables. */
export function getCurrentComfort(signal?: AbortSignal) {
  return request<ZoneComfort[]>(`${BASE}current/`, { signal });
}

export function getComfortHistory(zoneCode: string, period: { start: Date; end: Date }, signal?: AbortSignal) {
  return request<ComfortHistory>(`${BASE}zones/${encodeURIComponent(zoneCode)}/history/`, {
    query: { start: period.start, end: period.end, bucket_minutes: chartBucketMinutes(period.start, period.end) },
    signal,
  });
}

/** Personnalise les plages d'une zone (les champs absents gardent leur valeur). */
export function updateComfortProfile(zoneCode: string, changes: Partial<ComfortProfile>) {
  return request<ZoneComfort>(`${BASE}profiles/${encodeURIComponent(zoneCode)}/`, { method: "PATCH", body: changes });
}

/** Rétablit les plages par défaut du type d'espace. */
export function resetComfortProfile(zoneCode: string) {
  return request<ZoneComfort>(`${BASE}profiles/${encodeURIComponent(zoneCode)}/`, { method: "DELETE" });
}

export function getComfortProfile(zoneCode: string, signal?: AbortSignal) {
  return request<ZoneComfort>(`${BASE}profiles/${encodeURIComponent(zoneCode)}/`, { signal });
}
