import type { RealtimeStatus } from "../../types/common";

const LABELS: Record<RealtimeStatus, string> = {
  connected: "WebSocket connecté",
  connecting: "Connexion WebSocket",
  disconnected: "WebSocket interrompu",
};

/** Indique l'état de la connexion WebSocket avec l'API (pas l'état des capteurs). */
export function StatusPill({ status }: { status: RealtimeStatus }) {
  return (
    <div className={`status-pill status-${status}`} role="status">
      <span className="status-pulse" aria-hidden="true" />
      {LABELS[status]}
    </div>
  );
}
