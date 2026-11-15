import { openReconnectingSocket } from "../requests/realtimeSocket";
import type { Observation } from "../resources/observation";
import {
  parseRealtimeMessage,
  type AlertsState,
  type DashboardSnapshot,
  type RealtimeAction,
} from "../resources/realtime";
import type { Zone } from "../resources/zone";
import type { RealtimeStatus } from "../types/common";

export interface DashboardSubscription {
  /** État complet : à chaque (re)connexion et après `requestSnapshot()`. */
  onSnapshot: (snapshot: DashboardSnapshot) => void;
  onObservation: (observation: Observation) => void;
  onAlerts: (alerts: AlertsState) => void;
  onZones: (zones: Zone[]) => void;
  /** Le serveur n'a pas pu lire les données (base indisponible…). */
  onServerError: (detail: string) => void;
  onStatus: (status: RealtimeStatus) => void;
}

export interface DashboardConnection {
  /** Redemande l'instantané complet ; `false` si la connexion est coupée. */
  requestSnapshot: () => boolean;
  close: () => void;
}

const PING: RealtimeAction = { action: "ping" };
const SNAPSHOT: RealtimeAction = { action: "snapshot" };

/** S'abonne au flux temps réel du tableau de bord. */
export function subscribeToDashboard(handlers: DashboardSubscription): DashboardConnection {
  const socket = openReconnectingSocket("/ws/dashboard/", {
    keepAlive: PING,
    onStatus: handlers.onStatus,
    onMessage: (raw) => {
      const message = parseRealtimeMessage(raw);
      if (!message) return;
      switch (message.event) {
        case "dashboard.snapshot":
          handlers.onSnapshot(message.data);
          break;
        case "observation.created":
          handlers.onObservation(message.data);
          break;
        case "alerts.changed":
          handlers.onAlerts(message.data);
          break;
        case "zones.changed":
          handlers.onZones(message.data);
          break;
        case "dashboard.error":
          handlers.onServerError(message.detail);
          break;
        default:
          break;
      }
    },
  });
  return { requestSnapshot: () => socket.send(SNAPSHOT), close: socket.close };
}
