export type ComfortStatus = 'good' | 'warning' | 'critical';

export interface ComfortResult {
  spaceId: string | null;
  score: number;
  status: ComfortStatus;
  values: {
    temperature: number;
    humidity: number;
    co2: number;
    noise: number;
  };
  components: {
    temperature: number;
    humidity: number;
    co2: number;
    noise: number;
  };
}

export interface ComfortUnavailableResult {
  status: 'unavailable';
  message: string;
  missingTypes: string[];
}

export type ComfortResponse = ComfortResult | ComfortUnavailableResult;
