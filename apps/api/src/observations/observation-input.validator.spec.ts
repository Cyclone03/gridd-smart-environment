import { ObservationType } from './entities/observation.entity';
import { ObservationInput } from './interfaces/observation-input.interface';
import {
  InvalidObservationError,
  validateObservationInput,
} from './observation-input.validator';

describe('ObservationInput validation', () => {
  it.each([
    [ObservationType.TEMPERATURE, '°C'],
    [ObservationType.HUMIDITY, '%'],
    [ObservationType.CO2, 'ppm'],
    [ObservationType.SOUND_LEVEL, 'dBA'],
    [ObservationType.OCCUPANCY, 'person'],
  ])('accepts the unit for %s', (type, unit) => {
    expect(() => validateObservationInput(input({ type, unit }))).not.toThrow();
  });

  it.each([
    [{ nodeId: '' }, 'nodeId'],
    [{ value: Number.NaN }, 'value'],
    [{ unit: 'ppm' }, 'unit'],
    [{ observedAt: new Date('invalid') }, 'observedAt'],
    [{ metadata: [] as never }, 'metadata'],
  ])('rejects an invalid business field', (changes, expected) => {
    expect(() => validateObservationInput(input(changes))).toThrow(
      InvalidObservationError,
    );
    expect(() => validateObservationInput(input(changes))).toThrow(expected);
  });
});

function input(changes: Partial<ObservationInput> = {}): ObservationInput {
  return {
    nodeId: 'node-1',
    type: ObservationType.TEMPERATURE,
    value: 23,
    unit: '°C',
    observedAt: null,
    siteId: null,
    siteLabel: null,
    buildingId: null,
    buildingLabel: null,
    storeyId: null,
    storeyLabel: null,
    spaceId: null,
    spaceLabel: null,
    zoneId: null,
    zoneLabel: null,
    positionX: null,
    positionY: null,
    positionZ: null,
    metadata: null,
    ...changes,
  };
}
