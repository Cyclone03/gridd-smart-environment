import { ObservationType } from './entities/observation.entity';
import { ObservationInput } from './interfaces/observation-input.interface';
import { ObservationProcessor } from './observation.processor';
import { ObservationService } from './observations.service';

describe('ObservationProcessor', () => {
  const observationService = {
    create: jest.fn(),
  } as unknown as ObservationService;
  const processor = new ObservationProcessor(observationService);

  it('delegates persistence to ObservationService', async () => {
    const input = {
      nodeId: 'test-node',
      type: ObservationType.TEMPERATURE,
      value: 22,
      unit: '°C',
      observedAt: new Date(),
    } as ObservationInput;
    const persisted = { id: 'observation-id', ...input };
    jest.spyOn(observationService, 'create').mockResolvedValue(persisted as never);

    await expect(processor.process(input)).resolves.toBe(persisted);
    expect(observationService.create).toHaveBeenCalledWith(input);
  });
});
