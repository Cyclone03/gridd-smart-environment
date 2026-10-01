import { ObservationType } from './entities/observation.entity';
import { ObservationInput } from './interfaces/observation-input.interface';

const EXPECTED_UNITS: Readonly<Record<ObservationType, string>> = {
  [ObservationType.TEMPERATURE]: '°C',
  [ObservationType.HUMIDITY]: '%',
  [ObservationType.CO2]: 'ppm',
  [ObservationType.SOUND_LEVEL]: 'dBA',
  [ObservationType.OCCUPANCY]: 'person',
};

export class InvalidObservationError extends Error {}

export function validateObservationInput(input: ObservationInput): void {
  if (typeof input.nodeId !== 'string' || !input.nodeId.trim()) {
    throw new InvalidObservationError('nodeId is required');
  }
  if (!Object.values(ObservationType).includes(input.type)) {
    throw new InvalidObservationError(`unsupported observation type: ${input.type}`);
  }
  if (typeof input.value !== 'number' || !Number.isFinite(input.value)) {
    throw new InvalidObservationError('value must be a finite number');
  }
  if (input.unit !== EXPECTED_UNITS[input.type]) {
    throw new InvalidObservationError(`unit ${input.unit} is invalid for ${input.type}`);
  }
  if (
    input.observedAt != null &&
    (!(input.observedAt instanceof Date) || Number.isNaN(input.observedAt.getTime()))
  ) {
    throw new InvalidObservationError('observedAt must be a valid date or null');
  }
  if (
    input.metadata != null &&
    (typeof input.metadata !== 'object' || Array.isArray(input.metadata))
  ) {
    throw new InvalidObservationError('metadata must be a JSON object or null');
  }
}
