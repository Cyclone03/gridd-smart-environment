import { request } from "../requests/httpClient";
import type { Observation } from "../resources/observation";

/** Dernière mesure de chaque zone et de chaque type de mesure. */
export function getLatestObservations(signal?: AbortSignal) {
  return request<Observation[]>("/api/observations/latest/", { signal });
}
