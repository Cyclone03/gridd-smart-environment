import type { Observation, ObservationType } from '@/types/domain';

export type VisualStatus = 'normal' | 'good' | 'warning' | 'critical' | 'unavailable';

export function observationStatus(observation?: Observation): VisualStatus {
  if (!observation) return 'unavailable';
  const { type, value } = observation;
  if (type === 'temperature') {
    if (value < 18 || value > 28) return 'critical';
    if (value < 20 || value > 25) return 'warning';
  }
  if (type === 'humidity') {
    if (value < 20 || value > 70) return 'critical';
    if (value < 30 || value > 60) return 'warning';
  }
  if (type === 'co2') {
    if (value > 1200) return 'critical';
    if (value >= 800) return 'warning';
  }
  if (type === 'sound_level') {
    if (value > 70) return 'critical';
    if (value >= 55) return 'warning';
  }
  return 'normal';
}

export const metricLabels: Record<ObservationType, { label: string; icon: string }> = {
  temperature: { label: 'Température', icon: 'pi pi-sun' },
  humidity: { label: 'Humidité', icon: 'pi pi-percentage' },
  co2: { label: 'CO₂', icon: 'pi pi-cloud' },
  sound_level: { label: 'Niveau sonore', icon: 'pi pi-volume-up' },
  occupancy: { label: 'Occupation', icon: 'pi pi-users' },
};
