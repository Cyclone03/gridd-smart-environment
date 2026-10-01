import { Injectable } from '@nestjs/common';
import { AnalysisService } from '../analysis/analysis.service';
import { AlertsService } from '../alerts/alerts.service';
import { RealtimeGateway } from '../realtime/realtime.gateway';
import { Observation } from './entities/observation.entity';
import { ObservationInput } from './interfaces/observation-input.interface';
import { validateObservationInput } from './observation-input.validator';
import { ObservationService } from './observations.service';

@Injectable()
export class ObservationProcessor {
  constructor(
    private readonly observationService: ObservationService,
    private readonly analysisService: AnalysisService,
    private readonly alertsService: AlertsService,
    private readonly realtimeGateway: RealtimeGateway,
  ) {}

  async process(input: ObservationInput): Promise<Observation> {
    validateObservationInput(input);
    const observation = await this.observationService.create(input);
    this.realtimeGateway.emitObservationCreated(observation);

    const alertResult = await this.alertsService.evaluate(observation);
    if (alertResult.created) {
      this.realtimeGateway.emitAlertCreated(alertResult.created);
    }
    if (alertResult.resolved) {
      this.realtimeGateway.emitAlertResolved(alertResult.resolved);
    }

    const comfort = await this.analysisService.getCurrentComfort();
    if (comfort.status !== 'unavailable') {
      this.realtimeGateway.emitComfortUpdated(comfort);
    }

    return observation;
  }
}
