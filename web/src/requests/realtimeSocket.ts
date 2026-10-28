/**
 * Connexion WebSocket avec reconnexion automatique (transport bas niveau).
 * Le décodage des messages est fait par services/realtimeService.ts.
 */
import { REALTIME_RECONNECT_MS } from "../constants/app";
import type { RealtimeStatus } from "../types/common";
import { buildWsUrl } from "./config";

export interface SocketHandlers {
  onMessage: (data: string) => void;
  onStatus: (status: RealtimeStatus) => void;
}

/** Ouvre la connexion et retourne une fonction de fermeture définitive. */
export function openReconnectingSocket(path: string, handlers: SocketHandlers): () => void {
  let socket: WebSocket | null = null;
  let stopped = false;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;

  const connect = () => {
    if (stopped) return;
    handlers.onStatus("connecting");
    try {
      socket = new WebSocket(buildWsUrl(path));
    } catch {
      handlers.onStatus("disconnected");
      retryTimer = setTimeout(connect, REALTIME_RECONNECT_MS);
      return;
    }
    socket.onopen = () => handlers.onStatus("connected");
    socket.onmessage = (event) => handlers.onMessage(String(event.data));
    socket.onerror = () => handlers.onStatus("disconnected");
    socket.onclose = () => {
      handlers.onStatus("disconnected");
      if (!stopped) retryTimer = setTimeout(connect, REALTIME_RECONNECT_MS);
    };
  };

  connect();
  return () => {
    stopped = true;
    if (retryTimer) clearTimeout(retryTimer);
    socket?.close();
  };
}
