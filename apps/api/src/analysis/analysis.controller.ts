import { Controller, Get } from '@nestjs/common';
import { AnalysisService } from './analysis.service';
import { ComfortResponse } from './comfort.types';

@Controller('comfort')
export class AnalysisController {
  constructor(private readonly analysisService: AnalysisService) {}

  @Get()
  getCurrentComfort(): Promise<ComfortResponse> {
    return this.analysisService.getCurrentComfort();
  }
}
