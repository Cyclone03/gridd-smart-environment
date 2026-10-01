import { Repository } from 'typeorm';
import {
  Observation,
  ObservationType,
} from '../observations/entities/observation.entity';
import { AnalysisService } from './analysis.service';

const config = {
  thresholds: {
    temperature: { warningMin: 18, normalMin: 20, normalMax: 25, warningMax: 28 },
    humidity: { warningMin: 20, normalMin: 30, normalMax: 60, warningMax: 70 },
    co2: { normalMax: 800, warningMax: 1200 },
    soundLevel: { normalMax: 55, warningMax: 70 },
  },
  weights: { temperature: 0.3, humidity: 0.2, co2: 0.3, noise: 0.2 },
  status: { goodMin: 80, warningMin: 50 },
};

describe('AnalysisService', () => {
  const repository = {} as Repository<Observation>;
  const service = new AnalysisService(repository, config);

  it('calculates a good Comfort Index for normal values', () => {
    const result = service.calculateFromObservations(
      observations(22, 45, 600, 40),
    );

    expect(result).toEqual({
      spaceId: 'A-1540',
      score: 100,
      status: 'good',
      components: { temperature: 100, humidity: 100, co2: 100, noise: 100 },
    });
  });

  it('calculates a warning Comfort Index for attention-range values', () => {
    const result = service.calculateFromObservations(
      observations(27, 65, 1000, 62.5),
    );

    expect(result.status).toBe('warning');
    expect(result).toMatchObject({
      components: { temperature: 73, humidity: 80, co2: 80, noise: 80 },
    });
  });

  it('calculates a critical Comfort Index and clamps components to zero', () => {
    const result = service.calculateFromObservations(
      observations(32, 85, 1800, 90),
    );

    expect(result).toMatchObject({
      score: 0,
      status: 'critical',
      components: { temperature: 0, humidity: 0, co2: 0, noise: 0 },
    });
  });

  it('returns an explicit unavailable response when a required type is missing', () => {
    const result = service.calculateFromObservations(
      observations(22, 45, 600, 40).filter(
        ({ type }) => type !== ObservationType.CO2,
      ),
    );

    expect(result).toEqual({
      status: 'unavailable',
      message: 'Comfort index requires temperature, humidity, CO2 and sound level observations.',
      missingTypes: [ObservationType.CO2],
    });
  });
});

function observations(
  temperature: number,
  humidity: number,
  co2: number,
  sound: number,
): Observation[] {
  return [
    observation(ObservationType.TEMPERATURE, temperature),
    observation(ObservationType.HUMIDITY, humidity),
    observation(ObservationType.CO2, co2),
    observation(ObservationType.SOUND_LEVEL, sound),
  ];
}

function observation(type: ObservationType, value: number): Observation {
  return { type, value, spaceId: 'A-1540' } as Observation;
}
