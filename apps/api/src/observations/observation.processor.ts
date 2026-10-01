import { Injectable } from '@nestjs/common';
import { Observation } from './entities/observation.entity';
import { ObservationInput } from './interfaces/observation-input.interface';
import { ObservationService } from './observations.service';

@Injectable()
export class ObservationProcessor {
  constructor(private readonly observationService: ObservationService) {}

  process(input: ObservationInput): Promise<Observation> {
    return this.observationService.create(input);
  }
}
