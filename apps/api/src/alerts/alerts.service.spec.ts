import { Repository } from 'typeorm';
import {
  Observation,
  ObservationType,
} from '../observations/entities/observation.entity';
import { AlertsService } from './alerts.service';
import { Alert, AlertSeverity, AlertType } from './entities/alert.entity';

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

describe('AlertsService', () => {
  let service: AlertsService;
  let repository: {
    find: jest.Mock;
    findOne: jest.Mock;
    create: jest.Mock;
    save: jest.Mock;
  };

  beforeEach(() => {
    repository = {
      find: jest.fn(),
      findOne: jest.fn().mockResolvedValue(null),
      create: jest.fn((input) => ({ id: 'alert-id', ...input }) as Alert),
      save: jest.fn(async (alert) => alert as Alert),
    };
    service = new AlertsService(repository as unknown as Repository<Alert>, config);
  });

  it.each([
    [ObservationType.CO2, 1300, 'ppm', AlertType.HIGH_CO2, 1200],
    [ObservationType.SOUND_LEVEL, 71, 'dBA', AlertType.HIGH_SOUND_LEVEL, 70],
    [ObservationType.TEMPERATURE, 29, '°C', AlertType.HIGH_TEMPERATURE, 28],
  ])('detects a critical %s alert', async (type, value, unit, alertType, threshold) => {
    const result = await service.evaluate(observation(type, value, unit));

    expect(result.created).toMatchObject({
      type: alertType,
      severity: AlertSeverity.CRITICAL,
      value,
      threshold,
    });
  });

  it.each([
    [ObservationType.CO2, 800, 'ppm'],
    [ObservationType.CO2, 1000, 'ppm'],
    [ObservationType.CO2, 1200, 'ppm'],
    [ObservationType.SOUND_LEVEL, 55, 'dBA'],
    [ObservationType.SOUND_LEVEL, 65, 'dBA'],
    [ObservationType.SOUND_LEVEL, 70, 'dBA'],
    [ObservationType.TEMPERATURE, 25, '°C'],
    [ObservationType.TEMPERATURE, 27, '°C'],
    [ObservationType.TEMPERATURE, 28, '°C'],
  ])('does not create a %s alert at value %s', async (type, value, unit) => {
    await expect(service.evaluate(observation(type, value, unit))).resolves.toEqual(
      {},
    );
    expect(repository.create).not.toHaveBeenCalled();
    expect(repository.save).not.toHaveBeenCalled();
  });

  it('does not duplicate an equivalent active alert', async () => {
    repository.findOne.mockResolvedValue({
      id: 'active-alert',
      type: AlertType.HIGH_CO2,
      severity: AlertSeverity.CRITICAL,
      value: 1300,
      threshold: 1200,
    } as Alert);

    await expect(
      service.evaluate(observation(ObservationType.CO2, 1400, 'ppm')),
    ).resolves.toEqual({});
    expect(repository.create).not.toHaveBeenCalled();
    expect(repository.save).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'active-alert',
        severity: AlertSeverity.CRITICAL,
        value: 1400,
      }),
    );
  });

  it('resolves an active alert when the value returns to an acceptable level', async () => {
    const active = {
      id: 'active-alert',
      type: AlertType.HIGH_CO2,
      severity: AlertSeverity.CRITICAL,
      value: 1300,
      threshold: 1200,
      resolvedAt: null,
    } as Alert;
    repository.findOne.mockResolvedValue(active);

    const result = await service.evaluate(
      observation(ObservationType.CO2, 1000, 'ppm'),
    );

    expect(result.resolved).toBe(active);
    expect(active.resolvedAt).toBeInstanceOf(Date);
    expect(active.value).toBe(1000);
  });
});

function observation(
  type: ObservationType,
  value: number,
  unit: string,
): Observation {
  return {
    type,
    value,
    unit,
    nodeId: `node-${type}`,
    spaceId: 'A-1540',
  } as Observation;
}
