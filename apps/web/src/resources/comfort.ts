import type { ProfileErrors } from "./profile";

/**
 * Confort thermique. Contrat : /api/comfort/ (docs/api.md).
 * Le niveau est évalué par le backend à chaque mesure de température ou
 * d'humidité, selon les plages de confort de l'espace.
 */

export type ComfortLevel = "comfortable" | "acceptable" | "uncomfortable" | "unknown";
export type TemperatureStatus = "ok" | "cool" | "too_cold" | "warm" | "too_hot" | "unknown";
export type HumidityStatus = "ok" | "dry" | "too_dry" | "humid" | "too_humid" | "unknown";

export interface ComfortProfile {
  temperature_min: number;
  temperature_max: number;
  temperature_tolerance: number;
  humidity_min: number;
  humidity_max: number;
  humidity_tolerance: number;
}

export type ComfortProfileField = keyof ComfortProfile;

export interface ComfortAssessment {
  assessed_at: string;
  temperature: number | null;
  humidity: number | null;
  temperature_status: TemperatureStatus;
  humidity_status: HumidityStatus;
  level: ComfortLevel;
  /** 0 à 100. */
  score: number | null;
}

/** Zone, plages applicables et dernière évaluation (GET /api/comfort/current/). */
export interface ZoneComfort {
  zone_code: string;
  zone_name: string;
  zone_type: string;
  /** Vrai si les plages ont été personnalisées (sinon : valeurs par défaut du type d'espace). */
  customized: boolean;
  profile: ComfortProfile;
  assessment: ComfortAssessment | null;
}

/** Message temps réel `comfort.updated`. */
export interface ComfortUpdate extends ComfortAssessment {
  zone_code: string;
}

export interface ComfortHistoryPoint {
  time: string;
  score: number | null;
  temperature: number | null;
  humidity: number | null;
  comfortable: number;
  acceptable: number;
  uncomfortable: number;
}

export interface ComfortHistory {
  zone_code: string;
  start: string;
  end: string;
  bucket_minutes: number;
  profile: ComfortProfile;
  points: ComfortHistoryPoint[];
  summary: {
    count: number;
    average_score: number | null;
    comfortable_ratio: number | null;
    acceptable_ratio: number | null;
    uncomfortable_ratio: number | null;
  };
}

/** Contrôles croisés des plages (les bornes de chaque champ sont vérifiées à part). */
export function comfortProfileErrors(values: ComfortProfile): ProfileErrors<ComfortProfileField> {
  const errors: ProfileErrors<ComfortProfileField> = {};
  if (values.temperature_min >= values.temperature_max)
    errors.temperature_max = "La température maximale doit être supérieure à la minimale.";
  if (values.humidity_min >= values.humidity_max)
    errors.humidity_max = "L'humidité maximale doit être supérieure à la minimale.";
  return errors;
}

/** Applique une évaluation reçue en temps réel à la liste des zones. */
export function applyComfortUpdate(zones: ZoneComfort[], update: ComfortUpdate): ZoneComfort[] {
  return zones.map((zone) => {
    if (zone.zone_code !== update.zone_code) return zone;
    const current = zone.assessment;
    if (current && Date.parse(current.assessed_at) > Date.parse(update.assessed_at)) return zone;
    const { zone_code: _zoneCode, ...assessment } = update;
    return { ...zone, assessment };
  });
}
