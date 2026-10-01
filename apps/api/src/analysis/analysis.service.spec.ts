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

const repository = {} as Repository<Observation>;
const service = new AnalysisService(repository, config);

describe('AnalysisService', () => {
  it('calculates a good Comfort Index for normal values', () => {
    const result = service.calculateFromObservations(
      observations(22, 45, 600, 40),
    );

    expect(result).toEqual({
      spaceId: 'A-1540',
      score: 100,
      status: 'good',
      values: { temperature: 22, humidity: 45, co2: 600, noise: 40 },
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

  it('uses the exact source values from the same comfort calculation', () => {
    const result = service.calculateFromObservations(
      observations(25.6, 55.7, 1429, 79.4),
    );

    expect(result).toMatchObject({
      score: 60,
      status: 'warning',
      values: { temperature: 25.6, humidity: 55.7, co2: 1429, noise: 79.4 },
      components: { temperature: 92, humidity: 100, co2: 26, noise: 22 },
    });
  });

  describe.each([
    {
      metric: 'temperature',
      type: ObservationType.TEMPERATURE,
      cases: [
        [17, 'critical'], [18, 'attention'], [19, 'attention'],
        [20, 'normal'], [23, 'normal'], [25, 'normal'],
        [26, 'attention'], [28, 'attention'], [29, 'critical'],
      ],
    },
    {
      metric: 'humidity',
      type: ObservationType.HUMIDITY,
      cases: [
        [19, 'critical'], [20, 'attention'], [25, 'attention'],
        [30, 'normal'], [50, 'normal'], [60, 'normal'],
        [65, 'attention'], [70, 'attention'], [71, 'critical'],
      ],
    },
    {
      metric: 'co2',
      type: ObservationType.CO2,
      cases: [
        [500, 'normal'], [799, 'normal'], [800, 'attention'],
        [1000, 'attention'], [1200, 'attention'], [1201, 'critical'],
        [1500, 'critical'],
      ],
    },
    {
      metric: 'noise',
      type: ObservationType.SOUND_LEVEL,
      cases: [
        [40, 'normal'], [54, 'normal'], [55, 'attention'],
        [65, 'attention'], [70, 'attention'], [71, 'critical'],
        [80, 'critical'],
      ],
    },
  ] as const)('$metric component boundaries', ({ metric, type, cases }) => {
    it.each(cases)('scores %s in the %s range', (value, category) => {
      const score = componentScore(type, value);

      expect(score).toBeGreaterThanOrEqual(0);
      expect(score).toBeLessThanOrEqual(100);
      if (category === 'normal') expect(score).toBe(100);
      if (category === 'attention') {
        expect(score).toBeGreaterThanOrEqual(60);
        expect(score).toBeLessThanOrEqual(100);
      }
      if (category === 'critical') {
        expect(score).toBeGreaterThanOrEqual(0);
        expect(score).toBeLessThanOrEqual(60);
      }
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

function componentScore(type: ObservationType, value: number): number {
  const values = { temperature: 23, humidity: 50, co2: 500, sound: 40 };
  if (type === ObservationType.TEMPERATURE) values.temperature = value;
  if (type === ObservationType.HUMIDITY) values.humidity = value;
  if (type === ObservationType.CO2) values.co2 = value;
  if (type === ObservationType.SOUND_LEVEL) values.sound = value;
  const result = service.calculateFromObservations(
    observations(values.temperature, values.humidity, values.co2, values.sound),
  );
  if (result.status === 'unavailable') throw new Error('Expected comfort result');
  const key =
    type === ObservationType.TEMPERATURE
      ? 'temperature'
      : type === ObservationType.HUMIDITY
        ? 'humidity'
        : type === ObservationType.CO2
          ? 'co2'
          : 'noise';
  return result.components[key];
}
