import { Test, TestingModule } from '@nestjs/testing';
import { ObservationsController } from './observations.controller';
import { ObservationService } from './observations.service';

describe('ObservationsController', () => {
  let controller: ObservationsController;
  const observationsService = {
    findAll: jest.fn().mockResolvedValue([]),
    findLatest: jest.fn().mockResolvedValue([]),
  };

  beforeEach(async () => {
    jest.clearAllMocks();
    const module: TestingModule = await Test.createTestingModule({
      controllers: [ObservationsController],
      providers: [
        { provide: ObservationService, useValue: observationsService },
      ],
    }).compile();

    controller = module.get(ObservationsController);
  });

  it('returns all observations', async () => {
    await expect(controller.findAll()).resolves.toEqual([]);
    expect(observationsService.findAll).toHaveBeenCalledTimes(1);
  });

  it('returns the latest observations by type', async () => {
    await expect(controller.findLatest()).resolves.toEqual([]);
    expect(observationsService.findLatest).toHaveBeenCalledTimes(1);
  });
});
