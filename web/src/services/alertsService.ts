import { request } from "../requests/httpClient";
import type { Alert, AlertFilters } from "../resources/alert";

export function listAlerts(filters: AlertFilters = {}, signal?: AbortSignal) {
  return request<Alert[]>("/api/alerts/", {
    query: {
      active: filters.active,
      zone: filters.zone,
      rule: filters.rule,
      severity: filters.severity,
      since: filters.since,
      until: filters.until,
      limit: filters.limit,
    },
    signal,
  });
}

export function listActiveAlerts(signal?: AbortSignal) {
  return listAlerts({ active: true }, signal);
}
