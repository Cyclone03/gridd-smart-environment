import { BadRequestException } from '@nestjs/common';
import { Test, TestingModule } from '@nestjs/testing';
import { AlertsController } from './alerts.controller';
import { AlertsService } from './alerts.service';

describe('AlertsController', () => {
  let controller: AlertsController;
  const alertsService = { find: jest.fn().mockResolvedValue([]) };

  beforeEach(async () => {
    jest.clearAllMocks();
    const module: TestingModule = await Test.createTestingModule({
      controllers: [AlertsController],
      providers: [{ provide: AlertsService, useValue: alertsService }],
    }).compile();
    controller = module.get(AlertsController);
  });

  it.each(['active', 'history', 'all'])('supports the %s filter', async (filter) => {
    await expect(controller.find(filter)).resolves.toEqual([]);
    expect(alertsService.find).toHaveBeenCalledWith(filter);
  });

  it('rejects an unsupported filter', () => {
    expect(() => controller.find('invalid')).toThrow(BadRequestException);
  });
});
