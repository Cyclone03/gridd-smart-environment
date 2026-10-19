export type MetricType =
  | "temperature"
  | "humidity"
  | "co2"
  | "sound_level"
  | "occupancy";

export interface ThresholdProfile {
  enabled: boolean;
  temperature_min: number;
  temperature_max: number;
  humidity_min: number;
  humidity_max: number;
  co2_warning: number;
  co2_critical: number;
  sound_warning: number;
  sound_critical: number;
}

export interface Zone {
  id: number;
  name: string;
  code: string;
  zone_type: string;
  description: string;
  active: boolean;
  threshold_profile: ThresholdProfile;
}

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
  quality_status: "normal" | "suspicious" | "invalid";
  quality_reason: string;
}

export interface Alert {
  id: number;
  zone: number;
  zone_name: string;
  code: string;
  message: string;
  severity: "info" | "warning" | "critical";
  created_at: string;
  active: boolean;
}

export type RealtimeStatus = "connecting" | "connected" | "disconnected";
