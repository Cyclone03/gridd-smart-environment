/**
 * Paramètres des indicateurs de synthèse de la vue d'ensemble.
 *
 * Ce sont des repères internes au GRIDD, pas des normes. Le confort thermique
 * est, lui, évalué par le backend (module comfort) selon les plages de
 * chaque espace.
 */

/** Niveau sonore à partir duquel le confort sonore diminue (dBA). */
export const SOUND_COMFORT_FLOOR = 30;
/** Écart (dBA) au-delà du plancher qui ramène l'indice à 0. */
export const SOUND_COMFORT_SPAN = 50;

/** Capacité de référence du GRIDD pour le taux d'occupation (personnes). */
export const GRIDD_CAPACITY = 30;
