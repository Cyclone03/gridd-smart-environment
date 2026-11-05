import { request } from "../requests/httpClient";
import type { AlarmMetadata, AlarmRule, AlarmRulePayload } from "../resources/alarmRule";

const BASE = "/api/alarm-rules/";

let metadataCache: Promise<AlarmMetadata> | null = null;

/** Catalogue des paramètres, opérateurs et gravités (mis en cache). */
export function getAlarmMetadata(): Promise<AlarmMetadata> {
  metadataCache ??= request<AlarmMetadata>(`${BASE}metadata/`).catch((error: unknown) => {
    metadataCache = null;
    throw error;
  });
  return metadataCache;
}

export function listAlarmRules(filters: { zone?: string; metric?: string } = {}, signal?: AbortSignal) {
  return request<AlarmRule[]>(BASE, { query: filters, signal });
}

export function getAlarmRule(id: number, signal?: AbortSignal) {
  return request<AlarmRule>(`${BASE}${id}/`, { signal });
}

export function createAlarmRule(payload: AlarmRulePayload) {
  return request<AlarmRule>(BASE, { method: "POST", body: payload });
}

export function updateAlarmRule(id: number, changes: Partial<AlarmRulePayload>) {
  return request<AlarmRule>(`${BASE}${id}/`, { method: "PATCH", body: changes });
}

export function setAlarmRuleEnabled(id: number, enabled: boolean) {
  return updateAlarmRule(id, { enabled });
}

export function deleteAlarmRule(id: number) {
  return request<void>(`${BASE}${id}/`, { method: "DELETE" });
}
