export type ObservationType =
  | 'temperature'
  | 'humidity'
  | 'co2'
  | 'sound_level'
  | 'occupancy';

export interface Observation {
  id: string;
  nodeId: string;
  type: ObservationType;
  value: number;
  unit: string;
  observedAt: string | null;
  receivedAt: string;
  siteId: string | null;
  siteLabel: string | null;
  buildingId: string | null;
  buildingLabel: string | null;
  storeyId: string | null;
  storeyLabel: string | null;
  spaceId: string | null;
  spaceLabel: string | null;
  zoneId: string | null;
  zoneLabel: string | null;
  metadata: Record<string, unknown> | null;
}

export interface RealtimeObservation {
  id: string;
  nodeId: string;
  type: ObservationType;
  value: number;
  unit: string;
  observedAt: string | null;
  space: { id: string | null; label: string | null };
}

export type ComfortStatus = 'good' | 'warning' | 'critical';

export interface Comfort {
  spaceId: string | null;
  score: number;
  status: ComfortStatus;
  components: { temperature: number; humidity: number; co2: number; noise: number };
}

export interface ComfortUnavailable {
  status: 'unavailable';
  message: string;
  missingTypes: string[];
}

export type ComfortResponse = Comfort | ComfortUnavailable;

export type AlertType = 'HIGH_CO2' | 'HIGH_SOUND_LEVEL' | 'HIGH_TEMPERATURE';
export type AlertSeverity = 'warning' | 'critical';

export interface Alert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  value: number;
  threshold: number;
  unit: string;
  nodeId: string;
  spaceId: string | null;
  createdAt: string;
  resolvedAt: string | null;
}
