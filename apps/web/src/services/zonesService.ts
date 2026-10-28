import { request } from "../requests/httpClient";
import type { Zone } from "../resources/zone";

/** Espaces surveillés actifs, triés par nom. */
export function listZones(signal?: AbortSignal) {
  return request<Zone[]>("/api/zones/", { signal });
}
