/**
 * Connexion WebSocket avec reconnexion automatique (transport bas niveau).
 * Le décodage des messages est fait par services/realtimeService.ts.
 */
import { REALTIME_PING_MS, REALTIME_RECONNECT_MS } from "../constants/app";
import type { RealtimeStatus } from "../types/common";
import { buildWsUrl } from "./config";

export interface SocketHandlers {
  onMessage: (data: string) => void;
  onStatus: (status: RealtimeStatus) => void;
  /** Message JSON envoyé régulièrement pour garder la connexion ouverte. */
  keepAlive?: unknown;
}

export interface ReconnectingSocket {
  /** Envoie un message JSON ; retourne `false` si la connexion n'est pas ouverte. */
  send: (message: unknown) => boolean;
  /** Ferme définitivement la connexion (plus de reconnexion). */
  close: () => void;
}

/** Ouvre la connexion ; elle est rétablie automatiquement après une coupure. */
export function openReconnectingSocket(path: string, handlers: SocketHandlers): ReconnectingSocket {
  let socket: WebSocket | null = null;
  let stopped = false;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let pingTimer: ReturnType<typeof setInterval> | null = null;

  const send = (message: unknown) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify(message));
    return true;
  };

  const stopPing = () => {
    if (pingTimer) clearInterval(pingTimer);
    pingTimer = null;
  };

  const scheduleReconnect = () => {
    if (stopped || retryTimer) return;
    retryTimer = setTimeout(() => {
      retryTimer = null;
      connect();
    }, REALTIME_RECONNECT_MS);
  };

  const connect = () => {
    if (stopped) return;
    handlers.onStatus("connecting");
    let current: WebSocket;
    try {
      current = new WebSocket(buildWsUrl(path));
    } catch {
      handlers.onStatus("disconnected");
      scheduleReconnect();
      return;
    }
    socket = current;
    // Les événements d'une ancienne connexion (fermée entre-temps) sont ignorés.
    const isCurrent = () => socket === current && !stopped;
    current.onopen = () => {
      if (!isCurrent()) return;
      handlers.onStatus("connected");
      stopPing();
      if (handlers.keepAlive !== undefined) pingTimer = setInterval(() => send(handlers.keepAlive), REALTIME_PING_MS);
    };
    current.onmessage = (event) => {
      if (isCurrent()) handlers.onMessage(String(event.data));
    };
    current.onerror = () => {
      if (isCurrent()) handlers.onStatus("disconnected");
    };
    current.onclose = () => {
      if (!isCurrent()) return;
      stopPing();
      handlers.onStatus("disconnected");
      scheduleReconnect();
    };
  };

  connect();
  return {
    send,
    close: () => {
      stopped = true;
      stopPing();
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
      socket = null;
    },
  };
}
