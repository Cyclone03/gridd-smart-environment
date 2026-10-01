import { Controller, Get } from '@nestjs/common';
import { Observation } from './entities/observation.entity';
import { ObservationService } from './observations.service';

@Controller('observations')
export class ObservationsController {
  constructor(private readonly observationsService: ObservationService) {}

  @Get()
  findAll(): Promise<Observation[]> {
    return this.observationsService.findAll();
  }

  @Get('latest')
  findLatest(): Promise<Observation[]> {
    return this.observationsService.findLatest();
  }
}
