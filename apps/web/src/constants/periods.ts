import type { ObservationPeriod, PeriodPresetKey } from "../resources/period";

/**
 * Périodes prédéfinies des graphiques.
 *
 * Choisies d'après la fréquence réelle des capteurs (environ une mesure par
 * minute et par capteur) : en dessous de 15 minutes, un graphique compte trop
 * peu de points. Le backend agrège automatiquement les longues périodes.
 */
export interface PeriodPreset {
  key: PeriodPresetKey;
  label: string;
  /** Calcule les bornes de la période à l'instant `now`. */
  resolve: (now: Date) => { start: Date; end: Date };
  /** La fin suit l'heure courante (actualisation automatique). */
  live: boolean;
}

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

function startOfDay(date: Date) {
  const value = new Date(date);
  value.setHours(0, 0, 0, 0);
  return value;
}

function relative(durationMs: number) {
  return (now: Date) => ({ start: new Date(now.getTime() - durationMs), end: now });
}

export const PERIOD_PRESETS: PeriodPreset[] = [
  { key: "15m", label: "15 dernières minutes", resolve: relative(15 * MINUTE), live: true },
  { key: "1h", label: "Dernière heure", resolve: relative(HOUR), live: true },
  { key: "6h", label: "6 dernières heures", resolve: relative(6 * HOUR), live: true },
  { key: "24h", label: "24 dernières heures", resolve: relative(DAY), live: true },
  {
    key: "today",
    label: "Aujourd'hui",
    resolve: (now) => ({ start: startOfDay(now), end: now }),
    live: true,
  },
  {
    key: "yesterday",
    label: "Hier",
    resolve: (now) => {
      const end = startOfDay(now);
      const start = new Date(end);
      start.setDate(start.getDate() - 1);
      return { start, end };
    },
    live: false,
  },
  { key: "7d", label: "7 derniers jours", resolve: relative(7 * DAY), live: true },
  { key: "30d", label: "30 derniers jours", resolve: relative(30 * DAY), live: true },
];

export const DEFAULT_PERIOD: ObservationPeriod = { kind: "preset", preset: "today" };

/** Doit rester aligné sur HISTORY_MAX_RANGE_DAYS côté API. */
export const MAX_RANGE_DAYS = 31;

/** Intervalle d'actualisation des graphiques sur une période glissante. */
export const LIVE_PERIOD_REFRESH_MS = 60_000;

export function findPreset(key: string | null | undefined): PeriodPreset | undefined {
  return PERIOD_PRESETS.find((preset) => preset.key === key);
}
