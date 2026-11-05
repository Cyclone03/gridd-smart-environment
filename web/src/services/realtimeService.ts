import { openReconnectingSocket } from "../requests/realtimeSocket";
import type { ComfortUpdate } from "../resources/comfort";
import type { Observation } from "../resources/observation";
import { parseRealtimeMessage } from "../resources/realtime";
import type { RealtimeStatus } from "../types/common";

export interface DashboardSubscription {
  onObservation: (observation: Observation) => void;
  onAlertsChanged: () => void;
  onComfort: (update: ComfortUpdate) => void;
  onEnergy: (zoneCode: string) => void;
  onStatus: (status: RealtimeStatus) => void;
}

/** S'abonne au flux temps réel du tableau de bord. Retourne la désinscription. */
export function subscribeToDashboard(handlers: DashboardSubscription): () => void {
  return openReconnectingSocket("/ws/dashboard/", {
    onStatus: handlers.onStatus,
    onMessage: (raw) => {
      const message = parseRealtimeMessage(raw);
      if (!message) return;
      if (message.event === "observation.created") handlers.onObservation(message.data);
      else if (message.event === "alerts.changed") handlers.onAlertsChanged();
      else if (message.event === "comfort.updated") handlers.onComfort(message.data);
      else if (message.event === "energy.updated") handlers.onEnergy(message.data.zone_code);
    },
  });
}
