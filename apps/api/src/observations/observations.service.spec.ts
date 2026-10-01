import { Repository, SelectQueryBuilder } from 'typeorm';
import { Observation } from './entities/observation.entity';
import { ObservationInput } from './interfaces/observation-input.interface';
import { ObservationService } from './observations.service';

describe('ObservationService', () => {
  let service: ObservationService;
  let repository: jest.Mocked<
    Pick<Repository<Observation>, 'create' | 'save' | 'find' | 'createQueryBuilder'>
  >;
  let queryBuilder: jest.Mocked<
    Pick<
      SelectQueryBuilder<Observation>,
      'distinctOn' | 'orderBy' | 'addOrderBy' | 'getMany'
    >
  >;

  beforeEach(() => {
    queryBuilder = {
      distinctOn: jest.fn().mockReturnThis(),
      orderBy: jest.fn().mockReturnThis(),
      addOrderBy: jest.fn().mockReturnThis(),
      getMany: jest.fn(),
    };
    repository = {
      create: jest.fn(),
      save: jest.fn(),
      find: jest.fn(),
      createQueryBuilder: jest.fn().mockReturnValue(queryBuilder),
    };
    service = new ObservationService(
      repository as unknown as Repository<Observation>,
    );
  });

  it('persists an observation input', async () => {
    const input = { nodeId: 'simulator-temperature' } as ObservationInput;
    const observation = { id: 'observation-id', ...input } as Observation;
    repository.create.mockReturnValue(observation);
    repository.save.mockResolvedValue(observation);

    await expect(service.create(input)).resolves.toBe(observation);
    expect(repository.create).toHaveBeenCalledWith(input);
    expect(repository.save).toHaveBeenCalledWith(observation);
  });

  it('returns all observations ordered by reception date', async () => {
    repository.find.mockResolvedValue([]);

    await expect(service.findAll()).resolves.toEqual([]);
    expect(repository.find).toHaveBeenCalledWith({
      order: { receivedAt: 'DESC' },
    });
  });

  it('returns the latest observation for each type', async () => {
    queryBuilder.getMany.mockResolvedValue([]);

    await expect(service.findLatest()).resolves.toEqual([]);
    expect(queryBuilder.distinctOn).toHaveBeenCalledWith(['observation.type']);
    expect(queryBuilder.addOrderBy).toHaveBeenCalledWith(
      'COALESCE(observation.observedAt, observation.receivedAt)',
      'DESC',
    );
  });
});
