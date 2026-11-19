import type { Alert } from "./alert";
import type { Observation } from "./observation";
import type { Zone } from "./zone";
import { parseClimatePredictionData, type ClimatePrediction } from "./climatePrediction";
import { parseWeatherSnapshotData, type WeatherSnapshot } from "./weatherSnapshot";

export type { ClimatePrediction } from "./climatePrediction";
export type { WeatherSnapshot } from "./weatherSnapshot";

/**
 * Messages échangés sur le WebSocket `/ws/dashboard/` (voir docs/api.md).
 *
 * Le WebSocket est la seule source des données du tableau de bord : zones,
 * dernières mesures et alertes arrivent dans un instantané à la connexion,
 * puis sous forme de changements. Aucun appel HTTP périodique n'est fait.
 */

/** Alertes actives et alertes résolues récentes (page Alertes). */
export interface AlertsState {
  active: Alert[];
  history: Alert[];
  /** Profondeur de `history`, en jours (réglage serveur). */
  history_days?: number;
}

export interface DashboardSnapshot {
  zones: Zone[];
  latest: Observation[];
  alerts: AlertsState;
}

/** Messages reçus du serveur. */
export type RealtimeMessage =
  | { event: "realtime.connected" }
  | { event: "dashboard.snapshot"; data: DashboardSnapshot }
  | { event: "observation.created"; data: Observation }
  | { event: "climate_prediction.created"; data: ClimatePrediction }
  | { event: "weather_snapshot.created"; data: WeatherSnapshot }
  /** Lot de mesures (une seule diffusion par lot traité côté serveur). */
  | { event: "observations.created"; data: Observation[] }
  | { event: "alerts.changed"; data: AlertsState }
  | { event: "zones.changed"; data: Zone[] }
  | { event: "dashboard.error"; detail: string }
  | { event: "pong" };

/** Actions envoyées par le navigateur. */
export type RealtimeAction = { action: "snapshot" } | { action: "ping" };

export function parseRealtimeMessage(raw: string): RealtimeMessage | null {
  let message: { event?: unknown; data?: unknown; detail?: unknown };
  try {
    message = JSON.parse(raw) as typeof message;
  } catch {
    return null;
  }
  if (!isObject(message)) return null;
  const { data } = message;
  switch (message.event) {
    case "realtime.connected":
    case "pong":
      return { event: message.event };
    case "observation.created":
      return isObject(data) ? { event: "observation.created", data: data as Observation } : null;
    case "climate_prediction.created": {
      const prediction = parseClimatePredictionData(data);
      return prediction ? { event: "climate_prediction.created", data: prediction } : null;
    }
    case "weather_snapshot.created": {
      const snapshot = parseWeatherSnapshotData(data);
      return snapshot ? { event: "weather_snapshot.created", data: snapshot } : null;
    }
    case "observations.created":
      return Array.isArray(data) ? { event: "observations.created", data: data as Observation[] } : null;
    case "alerts.changed":
      return isAlertsState(data) ? { event: "alerts.changed", data } : null;
    case "zones.changed":
      return Array.isArray(data) ? { event: "zones.changed", data: data as Zone[] } : null;
    case "dashboard.snapshot":
      return isObject(data) &&
        Array.isArray((data as DashboardSnapshot).zones) &&
        Array.isArray((data as DashboardSnapshot).latest) &&
        isAlertsState((data as DashboardSnapshot).alerts)
        ? { event: "dashboard.snapshot", data: data as DashboardSnapshot }
        : null;
    case "dashboard.error":
      return {
        event: "dashboard.error",
        detail: typeof message.detail === "string" ? message.detail : "Données temporairement indisponibles.",
      };
    default:
      return null;
  }
}

function isAlertsState(value: unknown): value is AlertsState {
  return (
    isObject(value) && Array.isArray((value as AlertsState).active) && Array.isArray((value as AlertsState).history)
  );
}

function isObject(value: unknown): value is object {
  return Boolean(value) && typeof value === "object";
}
