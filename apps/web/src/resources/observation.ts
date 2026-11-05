/**
 * Mesures (observations) telles que renvoyées par l'API.
 * Contrat : GET /api/observations/latest/ et événements WebSocket
 * `observation.created` (voir docs/api.md).
 */

/** Types de mesure connus du backend. */
export type MetricType = "temperature" | "humidity" | "co2" | "sound_level" | "occupancy";

/** Types de mesure affichés par l'interface (le CO₂ n'est pas déployé). */
export type DisplayMetric = Exclude<MetricType, "co2">;

export type QualityStatus = "normal" | "suspicious" | "invalid";

export interface Observation {
  id: number;
  zone: number;
  zone_code?: string;
  zone_name: string;
  sensor: number;
  sensor_node_id: string;
  type: MetricType;
  value: number;
  unit: string;
  observed_at: string | null;
  received_at: string;
  quality_status: QualityStatus;
  quality_reason: string;
  metadata?: Record<string, unknown> & { source?: string };
}
