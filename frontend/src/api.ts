import type { Alert, Observation, Zone } from "./types";

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
    getJson<Observation[]>("/api/observations/"),
    getJson<Alert[]>("/api/alerts/?active=true"),
  ]);

  return { zones, observations, alerts };
}
