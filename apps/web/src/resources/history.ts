import type { MetricType } from "./observation";

/** Paramètres d'une requête d'historique (GET /api/zones/<code>/history/). */
export interface HistoryQuery {
  zoneCode: string;
  metric: MetricType;
  start: Date;
  end: Date;
  /** Granularité imposée ; par défaut le backend la choisit selon la durée. */
  bucketMinutes?: number;
}

export interface HistoryPoint {
  /** Début du créneau (ISO 8601, fuseau du serveur). */
  time: string;
  average: number;
  minimum: number;
  maximum: number;
  count: number;
  suspicious_count: number;
}

export type Trend = "rising" | "falling" | "stable";

export interface ZoneHistory {
  zone_code: string;
  type: MetricType;
  start: string;
  end: string;
  timezone: string;
  hours: number;
  date?: string | null;
  bucket_minutes: number;
  unit: string;
  points: HistoryPoint[];
  statistics: {
    minimum: number | null;
    maximum: number | null;
    average: number | null;
    count: number;
    trend: Trend;
  };
}
