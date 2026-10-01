import { ConfigService } from '@nestjs/config';
import { ObservationType } from '../observations/entities/observation.entity';
import { ObservationProcessor } from '../observations/observation.processor';
import { SimulatorService } from './simulator.service';

describe('SimulatorService', () => {
  const processor = {
    process: jest.fn(async (input) => ({ id: 'generated-id', ...input })),
  } as unknown as ObservationProcessor;

  afterEach(() => {
    jest.restoreAllMocks();
    jest.useRealTimers();
  });

  it('does not generate observations when disabled', () => {
    const service = createService({ SIMULATOR_ENABLED: 'false' });

    service.onModuleInit();

    expect(processor.process).not.toHaveBeenCalled();
  });

  it('generates all five realistic observation types through the processor', async () => {
    jest.spyOn(Math, 'random').mockReturnValue(0.5);
    const service = createService({ SIMULATOR_ENABLED: 'false' });

    await service.generateOnce();

    expect(processor.process).toHaveBeenCalledTimes(5);
    const inputs = jest.mocked(processor.process).mock.calls.map(([input]) => input);
    expect(inputs.map(({ type }) => type)).toEqual([
      ObservationType.TEMPERATURE,
      ObservationType.HUMIDITY,
      ObservationType.CO2,
      ObservationType.SOUND_LEVEL,
      ObservationType.OCCUPANCY,
    ]);
    expect(inputs.map(({ value }) => value)).toEqual([24, 47.5, 1000, 55, 13]);
    expect(inputs[0].metadata).toMatchObject({
      source: 'simulator',
      space: { id: 'A-1540', label: 'GRIDD', type: 'laboratory' },
      position: { unit: 'm', coordinateSystem: 'A-1540-local' },
    });
  });

  it('generates immediately and then at the configured interval when enabled', async () => {
    jest.useFakeTimers();
    const service = createService({
      SIMULATOR_ENABLED: 'true',
      SIMULATOR_INTERVAL_MS: '1000',
    });

    service.onModuleInit();
    expect(processor.process).toHaveBeenCalledTimes(5);

    await jest.advanceTimersByTimeAsync(1000);
    expect(processor.process).toHaveBeenCalledTimes(10);
    service.onModuleDestroy();
  });

  function createService(values: Record<string, string>): SimulatorService {
    jest.clearAllMocks();
    const configService = {
      get: jest.fn((key: string, fallback: string) => values[key] ?? fallback),
    } as unknown as ConfigService;
    return new SimulatorService(configService, processor);
  }
});
