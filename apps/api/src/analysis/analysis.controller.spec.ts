import { Test, TestingModule } from '@nestjs/testing';
import { AnalysisController } from './analysis.controller';
import { AnalysisService } from './analysis.service';

describe('AnalysisController', () => {
  let controller: AnalysisController;
  const analysisService = {
    getCurrentComfort: jest.fn().mockResolvedValue({
      spaceId: 'A-1540',
      score: 100,
      status: 'good',
      components: { temperature: 100, humidity: 100, co2: 100, noise: 100 },
    }),
  };

  beforeEach(async () => {
    jest.clearAllMocks();
    const module: TestingModule = await Test.createTestingModule({
      controllers: [AnalysisController],
      providers: [{ provide: AnalysisService, useValue: analysisService }],
    }).compile();
    controller = module.get(AnalysisController);
  });

  it('returns the current Comfort Index', async () => {
    await expect(controller.getCurrentComfort()).resolves.toMatchObject({
      spaceId: 'A-1540',
      status: 'good',
    });
  });
});
