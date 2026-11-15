/** Constantes générales de l'application. */

export const APP_NAME = "GRIDD";
export const SITE_LABEL = "ÉTS · Pavillon A · A-1540";

/** Délai avant une nouvelle tentative de connexion WebSocket. */
export const REALTIME_RECONNECT_MS = 3_000;
/**
 * Message de maintien de connexion envoyé sur le WebSocket : évite qu'un
 * proxy (nginx coupe par défaut après 60 s d'inactivité) ferme la connexion.
 */
export const REALTIME_PING_MS = 25_000;
/**
 * Les mesures reçues sont regroupées sur ce délai avant d'être appliquées :
 * une rafale de mesures ne provoque qu'un seul rendu.
 */
export const REALTIME_BATCH_MS = 250;
/**
 * Au-delà de ce délai sans nouvelle mesure, la dernière valeur d'un capteur
 * est signalée comme « pas à jour » (les capteurs émettent toutes les 5 à 40 s)
 * et n'entre plus dans les moyennes du laboratoire.
 */
export const STALE_READING_MS = 10 * 60_000;
/** Fréquence de réévaluation de la fraîcheur des mesures. */
export const NOW_TICK_MS = 30_000;
/** Délai maximal d'une requête HTTP. */
export const REQUEST_TIMEOUT_MS = 15_000;

/** Clés de stockage local (préférences propres à chaque navigateur). */
export const STORAGE_KEYS = {
  readAlerts: "gridd-alerts-read-ids",
} as const;

export const LOCALE = "fr-CA";
