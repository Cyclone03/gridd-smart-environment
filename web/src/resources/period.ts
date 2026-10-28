import type { FieldErrors } from "../types/common";

/**
 * Période d'observation d'un graphique.
 *
 * - `preset` : période relative (ex. « dernière heure »), recalculée à chaque
 *   actualisation pour suivre l'heure courante ;
 * - `custom` : bornes fixes choisies par l'utilisateur (ISO 8601).
 */
export type PeriodPresetKey = "15m" | "1h" | "6h" | "24h" | "today" | "yesterday" | "7d" | "30d";

export type ObservationPeriod =
  | { kind: "preset"; preset: PeriodPresetKey }
  | { kind: "custom"; start: string; end: string };

/** Bornes effectives d'une période à un instant donné. */
export interface ResolvedPeriod {
  start: Date;
  end: Date;
  /** Libellé lisible de la période appliquée. */
  label: string;
  /** Vrai si la période suit l'heure courante et doit être actualisée. */
  live: boolean;
}

export type CustomRangeField = "start" | "end";

/**
 * Valide une plage personnalisée saisie dans des champs `datetime-local`.
 * La limite de durée reprend celle du backend (HISTORY_MAX_RANGE_DAYS) ; le
 * backend reste l'autorité et renverra une erreur explicite si elle diffère.
 */
export function validateCustomRange(
  startInput: string,
  endInput: string,
  { now = new Date(), maxRangeDays }: { now?: Date; maxRangeDays: number },
): { errors: FieldErrors<CustomRangeField>; start?: Date; end?: Date } {
  const errors: FieldErrors<CustomRangeField> = {};
  const start = startInput ? new Date(startInput) : null;
  const end = endInput ? new Date(endInput) : null;

  if (!start || Number.isNaN(start.getTime())) errors.start = "Indiquez une date et une heure de début valides.";
  if (!end || Number.isNaN(end.getTime())) errors.end = "Indiquez une date et une heure de fin valides.";
  if (errors.start || errors.end || !start || !end) return { errors };

  if (start > now) errors.start = "Le début ne peut pas être dans le futur.";
  if (end <= start) errors.end = "La fin doit être postérieure au début.";
  else if (end.getTime() - start.getTime() > maxRangeDays * 86_400_000)
    errors.end = `La période ne peut pas dépasser ${maxRangeDays} jours.`;

  return Object.keys(errors).length ? { errors } : { errors, start, end };
}
