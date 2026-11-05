import { request } from "../requests/httpClient";
import type { EnergyProfile, EnergySeries, EnergySummary, PeriodQuery, ZoneEnergyProfile } from "../resources/energy";
import { chartBucketMinutes } from "../utils/period";

const BASE = "/api/energy/";

/** Énergie estimée par zone et au total sur une période. */
export function getEnergySummary(period: PeriodQuery, signal?: AbortSignal) {
  return request<EnergySummary>(`${BASE}summary/`, { query: { start: period.start, end: period.end }, signal });
}

/** Énergie estimée d'une zone, par créneau et par usage. */
export function getEnergySeries(zoneCode: string, period: PeriodQuery, signal?: AbortSignal) {
  return request<EnergySeries>(`${BASE}zones/${encodeURIComponent(zoneCode)}/series/`, {
    query: { start: period.start, end: period.end, bucket_minutes: chartBucketMinutes(period.start, period.end) },
    signal,
  });
}

export function getEnergyProfile(zoneCode: string, signal?: AbortSignal) {
  return request<ZoneEnergyProfile>(`${BASE}profiles/${encodeURIComponent(zoneCode)}/`, { signal });
}

/** Personnalise les paramètres du modèle d'une zone. */
export function updateEnergyProfile(zoneCode: string, changes: Partial<EnergyProfile>) {
  return request<ZoneEnergyProfile>(`${BASE}profiles/${encodeURIComponent(zoneCode)}/`, {
    method: "PATCH",
    body: changes,
  });
}

/** Rétablit les paramètres par défaut du type d'espace. */
export function resetEnergyProfile(zoneCode: string) {
  return request<ZoneEnergyProfile>(`${BASE}profiles/${encodeURIComponent(zoneCode)}/`, { method: "DELETE" });
}
