/**
 * Outils de test : faux backend (fetch simulé) et rendu de l'application
 * complète sur une route donnée, avec les vrais services et stores.
 */
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { vi } from "vitest";
import type { AlarmMetadata, AlarmRule } from "../src/resources/alarmRule";
import type { Observation } from "../src/resources/observation";
import type { Zone } from "../src/resources/zone";
import type { ZoneHistory } from "../src/resources/history";
import { routes } from "../src/routes";
import { AuthProvider } from "../src/stores/authStore";
import { DashboardProvider } from "../src/stores/dashboardStore";

export interface RecordedRequest {
  method: string;
  path: string;
  query: URLSearchParams;
  body: unknown;
  headers: Record<string, string>;
}

type Handler = (request: RecordedRequest) => { status?: number; body?: unknown } | undefined;

/** Installe un faux `fetch` : chaque requête est enregistrée puis routée. */
export function mockApi(handler: Handler) {
  const requests: RecordedRequest[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    const request: RecordedRequest = {
      method: init?.method ?? "GET",
      path: url.pathname,
      query: url.searchParams,
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
      headers: (init?.headers ?? {}) as Record<string, string>,
    };
    requests.push(request);
    const result = handler(request) ?? { status: 404, body: { detail: "Introuvable (test)." } };
    const status = result.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(result.body ?? {}), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { requests, fetchMock };
}

export const zones: Zone[] = [
  {
    id: 1,
    name: "Salle de réunion",
    code: "meeting-room",
    zone_type: "meeting_room",
    description: "",
    active: true,
    metrics: ["temperature", "humidity", "sound_level"],
    threshold_profile: null,
  },
  {
    id: 2,
    name: "occupancy-camera",
    code: "occupancy-camera",
    zone_type: "other",
    description: "",
    active: true,
    metrics: ["occupancy"],
    threshold_profile: null,
  },
];

export const observations: Observation[] = [
  {
    id: 10,
    zone: 1,
    zone_code: "meeting-room",
    zone_name: "Salle de réunion",
    sensor: 1,
    sensor_node_id: "env-1",
    type: "temperature",
    value: 22.4,
    unit: "C",
    observed_at: "2026-10-27T12:00:00Z",
    received_at: "2026-10-27T12:00:01Z",
    quality_status: "normal",
    quality_reason: "",
  },
  {
    id: 11,
    zone: 2,
    zone_code: "occupancy-camera",
    zone_name: "occupancy-camera",
    sensor: 2,
    sensor_node_id: "cam",
    type: "occupancy",
    value: 6,
    unit: "person",
    observed_at: "2026-10-27T12:00:00Z",
    received_at: "2026-10-27T12:00:01Z",
    quality_status: "normal",
    quality_reason: "",
  },
];

export function history(points: number, overrides: Partial<ZoneHistory> = {}): ZoneHistory {
  return {
    zone_code: "meeting-room",
    type: "temperature",
    start: "2026-10-27T00:00:00-04:00",
    end: "2026-10-27T12:00:00-04:00",
    timezone: "America/Toronto",
    hours: 12,
    date: null,
    bucket_minutes: 5,
    unit: "°C",
    points: Array.from({ length: points }, (_, index) => ({
      time: new Date(Date.UTC(2026, 9, 27, 4, index * 5)).toISOString(),
      average: 21 + index / 10,
      minimum: 21,
      maximum: 22,
      count: 3,
      suspicious_count: 0,
    })),
    statistics: { minimum: 21, maximum: 23, average: 22, count: points * 3, trend: points > 1 ? "rising" : "stable" },
    ...overrides,
  };
}

export const metadata: AlarmMetadata = {
  metrics: [
    {
      key: "temperature",
      label: "Température",
      unit: "°C",
      integer: false,
      min: -20,
      max: 60,
      operators: ["gt", "gte", "lt", "lte", "outside_range", "inside_range"],
    },
    {
      key: "occupancy",
      label: "Occupation",
      unit: "personnes",
      integer: true,
      min: 0,
      max: 500,
      operators: ["gt", "gte", "lt", "lte", "outside_range", "inside_range"],
    },
  ],
  operators: [
    { key: "gt", label: "Supérieur à", symbol: ">", range: false },
    { key: "gte", label: "Supérieur ou égal à", symbol: "≥", range: false },
    { key: "lt", label: "Inférieur à", symbol: "<", range: false },
    { key: "lte", label: "Inférieur ou égal à", symbol: "≤", range: false },
    { key: "outside_range", label: "En dehors de l'intervalle", symbol: null, range: true },
    { key: "inside_range", label: "À l'intérieur de l'intervalle", symbol: null, range: true },
  ],
  severities: [
    { key: "info", label: "Info" },
    { key: "warning", label: "Attention" },
    { key: "critical", label: "Critique" },
  ],
  max_duration_seconds: 86400,
};

export function rule(overrides: Partial<AlarmRule> = {}): AlarmRule {
  return {
    id: 7,
    name: "Trop chaud",
    description: "",
    zone: "meeting-room",
    zone_name: "Salle de réunion",
    metric: "temperature",
    operator: "gt",
    threshold: 28,
    threshold_high: null,
    unit: "°C",
    condition_label: "> 28 °C",
    enabled: true,
    severity: "warning",
    min_duration_seconds: 300,
    hysteresis: 0.5,
    active_alerts: 0,
    created_at: "2026-10-27T10:00:00Z",
    updated_at: "2026-10-27T10:00:00Z",
    created_by: "gestion",
    updated_by: "gestion",
    ...overrides,
  };
}

export const manager = {
  username: "gestion",
  display_name: "Gestion Alarmes",
  is_staff: false,
  permissions: { alarm_rules: { add: true, change: true, delete: true } },
};

/** Réponses communes du tableau de bord ; `extra` traite les autres requêtes. */
export function dashboardApi(extra: Handler = () => undefined, { user = null as typeof manager | null } = {}) {
  return mockApi((request) => {
    const custom = extra(request);
    if (custom) return custom;
    if (request.path === "/api/zones/") return { body: zones };
    if (request.path === "/api/observations/latest/") return { body: observations };
    if (request.path === "/api/alerts/") return { body: [] };
    if (request.path === "/api/auth/me/")
      return user ? { body: user } : { status: 401, body: { detail: "Authentification requise." } };
    if (request.path === "/api/alarm-rules/metadata/") return { body: metadata };
    return undefined;
  });
}

/** Rend l'application complète sur `path`. Avec `token`, une session est restaurée. */
export function renderApp(path: string, { token }: { token?: string } = {}) {
  if (token) window.localStorage.setItem("gridd-auth-token", token);
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const view = render(
    <AuthProvider>
      <DashboardProvider realtime={false}>
        <RouterProvider router={router} />
      </DashboardProvider>
    </AuthProvider>,
  );
  return { ...view, router };
}
