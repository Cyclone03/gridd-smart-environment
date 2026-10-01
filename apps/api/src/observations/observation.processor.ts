import { Injectable } from '@nestjs/common';
import { AnalysisService } from '../analysis/analysis.service';
import { AlertsService } from '../alerts/alerts.service';
import { RealtimeGateway } from '../realtime/realtime.gateway';
import {
  KafkaProducerService,
  KafkaPublicationContext,
} from '../kafka/kafka.producer.service';
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
    private readonly kafkaProducer: KafkaProducerService,
  ) {}

  async process(input: ObservationInput): Promise<Observation> {
    validateObservationInput(input);
    const observation = await this.observationService.create(input);
    this.realtimeGateway.emitObservationCreated(observation);

    const alertResult = await this.alertsService.evaluate(observation);
    const publicationContext: KafkaPublicationContext = {
      spaceId: observation.spaceId,
      spaceLabel: observation.spaceLabel,
      timestamp: observation.observedAt ?? observation.receivedAt ?? new Date(),
    };
    if (alertResult.created) {
      this.realtimeGateway.emitAlertCreated(alertResult.created);
      this.ignorePublicationFailure(
        this.kafkaProducer.publishAlert(alertResult.created, publicationContext),
      );
    }
    if (alertResult.resolved) {
      this.realtimeGateway.emitAlertResolved(alertResult.resolved);
    }

    const comfort = await this.analysisService.getCurrentComfort();
    if (comfort.status !== 'unavailable') {
      this.realtimeGateway.emitComfortUpdated(comfort);
      this.ignorePublicationFailure(
        this.kafkaProducer.publishComfort(comfort, publicationContext),
      );
    }

    return observation;
  }

  private ignorePublicationFailure(publication: Promise<boolean>): void {
    void publication.catch(() => undefined);
  }
}
