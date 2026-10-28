/** Constantes générales de l'application. */

export const APP_NAME = "GRIDD";
export const SITE_LABEL = "ÉTS · Pavillon A · A-1540";

/** Rafraîchissement complet du tableau de bord (en plus du temps réel). */
export const DASHBOARD_REFRESH_MS = 60_000;
/** Délai avant une nouvelle tentative de connexion WebSocket. */
export const REALTIME_RECONNECT_MS = 3_000;
/** Nombre maximal d'observations temps réel conservées en mémoire. */
export const MAX_LIVE_OBSERVATIONS = 1_000;
/** Délai maximal d'une requête HTTP. */
export const REQUEST_TIMEOUT_MS = 15_000;

/** Clés de stockage local (préférences propres à chaque navigateur). */
export const STORAGE_KEYS = {
  readAlerts: "gridd-alerts-read-ids",
  authToken: "gridd-auth-token",
} as const;

export const LOCALE = "fr-CA";
