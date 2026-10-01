import { io, type Socket } from 'socket.io-client';
import type { Alert, Comfort, RealtimeObservation } from '@/types/domain';

const SOCKET_URL = (import.meta.env.VITE_SOCKET_URL || 'http://localhost:3000').replace(
  /\/$/,
  '',
);

export interface RealtimeHandlers {
  onConnectionChange: (connected: boolean) => void;
  onError: (message: string) => void;
  onObservation: (observation: RealtimeObservation) => void;
  onAlertCreated: (alert: Alert) => void;
  onAlertResolved: (alert: Alert) => void;
  onComfort: (comfort: Comfort) => void;
}

let socket: Socket | undefined;

export function connectRealtime(handlers: RealtimeHandlers): () => void {
  socket ??= io(`${SOCKET_URL}/realtime`, {
    autoConnect: false,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
  });

  const connected = () => handlers.onConnectionChange(true);
  const disconnected = () => handlers.onConnectionChange(false);
  const connectError = () => {
    handlers.onConnectionChange(false);
    handlers.onError('Connexion temps réel indisponible. Reconnexion en cours…');
  };

  socket.on('connect', connected);
  socket.on('disconnect', disconnected);
  socket.on('connect_error', connectError);
  socket.on('observation.created', handlers.onObservation);
  socket.on('alert.created', handlers.onAlertCreated);
  socket.on('alert.resolved', handlers.onAlertResolved);
  socket.on('comfort.updated', handlers.onComfort);
  if (!socket.connected) socket.connect();

  return () => {
    socket?.off('connect', connected);
    socket?.off('disconnect', disconnected);
    socket?.off('connect_error', connectError);
    socket?.off('observation.created', handlers.onObservation);
    socket?.off('alert.created', handlers.onAlertCreated);
    socket?.off('alert.resolved', handlers.onAlertResolved);
    socket?.off('comfort.updated', handlers.onComfort);
  };
}
