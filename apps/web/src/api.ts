import type { Alert, MetricType, Observation, Zone, ZoneHistory } from "./types";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`La requête ${path} a échoué (${response.status}).`);
  }

  return response.json() as Promise<T>;
}

export async function loadDashboard() {
  const [zones, observations, alerts] = await Promise.all([
    getJson<Zone[]>("/api/zones/"),
    loadLatestObservations(),
    getJson<Alert[]>("/api/alerts/?active=true"),
  ]);

  return { zones, observations, alerts };
}

export function loadLatestObservations() {
  return getJson<Observation[]>("/api/observations/latest/");
}

export function loadActiveAlerts() {
  return getJson<Alert[]>("/api/alerts/?active=true");
}

export function loadZoneHistory(
  zoneCode: string,
  type: MetricType,
  hours: 1 | 6 | 24 | 168,
) {
  const query = new URLSearchParams({ type, hours: String(hours) });
  return getJson<ZoneHistory>(
    `/api/zones/${encodeURIComponent(zoneCode)}/history/?${query}`,
  );
}

export function loadZoneDayHistory(
  zoneCode: string,
  type: MetricType,
  date: string,
) {
  const query = new URLSearchParams({ type, date });
  return getJson<ZoneHistory>(
    `/api/zones/${encodeURIComponent(zoneCode)}/history/?${query}`,
  );
}
