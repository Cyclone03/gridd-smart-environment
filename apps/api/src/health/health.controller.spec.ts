import { Test, TestingModule } from '@nestjs/testing';
import { HealthController } from './health.controller';
import { HealthService } from './health.service';

describe('HealthController', () => {
  let controller: HealthController;
  const healthService = {
    check: jest.fn().mockResolvedValue({
      status: 'ok',
      database: 'connected',
    }),
  };

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [HealthController],
      providers: [{ provide: HealthService, useValue: healthService }],
    }).compile();

    controller = module.get<HealthController>(HealthController);
  });

  it('returns the API and database status', async () => {
    await expect(controller.getHealth()).resolves.toEqual({
      status: 'ok',
      database: 'connected',
    });
  });
});
