import type { MetricType } from "./observation";

/** Paramètres de qualité des données d'une zone (les seuils d'alarme sont des règles). */
export interface ThresholdProfile {
  enabled: boolean;
  max_temperature_delta_per_minute: number;
  max_humidity_delta_per_minute: number;
  max_co2_delta_per_minute: number;
  max_sound_delta_per_minute: number | null;
  stuck_after_minutes: number;
}

/** Espace surveillé. Contrat : GET /api/zones/. */
export interface Zone {
  id: number;
  name: string;
  code: string;
  zone_type: string;
  description: string;
  active: boolean;
  /** Types de mesure disposant d'un capteur actif dans la zone. */
  metrics: MetricType[];
  threshold_profile: ThresholdProfile | null;
}
