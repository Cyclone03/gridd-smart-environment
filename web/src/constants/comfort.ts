/**
 * Paramètres des indicateurs de synthèse de la vue d'ensemble.
 *
 * Ce sont des repères internes au GRIDD, pas des normes : ils doivent être
 * ajustés selon l'usage des espaces. Les alarmes, elles, se configurent avec
 * les règles d'alarme.
 */

/** Température jugée idéale pour l'indice de confort thermique (°C). */
export const THERMAL_TARGET_TEMPERATURE = 25;
/** Humidité jugée idéale pour l'indice de confort thermique (%). */
export const THERMAL_TARGET_HUMIDITY = 35;
/** Pondérations température / humidité de l'indice de confort thermique. */
export const THERMAL_WEIGHTS = { temperature: 0.7, humidity: 0.3 } as const;

/** Niveau sonore à partir duquel le confort sonore diminue (dBA). */
export const SOUND_COMFORT_FLOOR = 30;
/** Écart (dBA) au-delà du plancher qui ramène l'indice à 0. */
export const SOUND_COMFORT_SPAN = 50;

/** Capacité de référence du GRIDD pour le taux d'occupation (personnes). */
export const GRIDD_CAPACITY = 30;
