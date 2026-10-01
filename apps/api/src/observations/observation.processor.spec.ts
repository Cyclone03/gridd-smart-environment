import { AnalysisService } from '../analysis/analysis.service';
import { AlertsService } from '../alerts/alerts.service';
import { KafkaProducerService } from '../kafka/kafka.producer.service';
import { RealtimeGateway } from '../realtime/realtime.gateway';
import { ObservationType } from './entities/observation.entity';
import { ObservationInput } from './interfaces/observation-input.interface';
import { ObservationProcessor } from './observation.processor';
import { ObservationService } from './observations.service';

describe('ObservationProcessor', () => {
  const observationService = {
    create: jest.fn(),
  } as unknown as ObservationService;
  const analysisService = {
    getCurrentComfort: jest.fn(),
  } as unknown as AnalysisService;
  const alertsService = { evaluate: jest.fn() } as unknown as AlertsService;
  const realtimeGateway = {
    emitObservationCreated: jest.fn(),
    emitAlertCreated: jest.fn(),
    emitAlertResolved: jest.fn(),
    emitComfortUpdated: jest.fn(),
  } as unknown as RealtimeGateway;
  const kafkaProducer = {
    publishAlert: jest.fn().mockResolvedValue(true),
    publishComfort: jest.fn().mockResolvedValue(true),
  } as unknown as KafkaProducerService;
  const processor = new ObservationProcessor(
    observationService,
    analysisService,
    alertsService,
    realtimeGateway,
    kafkaProducer,
  );

  beforeEach(() => jest.clearAllMocks());

  it('delegates persistence to ObservationService', async () => {
    const input = {
      nodeId: 'test-node',
      type: ObservationType.TEMPERATURE,
      value: 22,
      unit: '°C',
      observedAt: new Date(),
    } as ObservationInput;
    const persisted = { id: 'observation-id', ...input };
    jest.spyOn(observationService, 'create').mockResolvedValue(persisted as never);
    jest.spyOn(alertsService, 'evaluate').mockResolvedValue({});
    jest.spyOn(analysisService, 'getCurrentComfort').mockResolvedValue({
      status: 'unavailable',
      message: 'missing data',
      missingTypes: ['co2'],
    });

    await expect(processor.process(input)).resolves.toBe(persisted);
    expect(observationService.create).toHaveBeenCalledWith(input);
    expect(realtimeGateway.emitObservationCreated).toHaveBeenCalledWith(persisted);
    expect(alertsService.evaluate).toHaveBeenCalledWith(persisted);
  });

  it('broadcasts created alerts and available comfort results', async () => {
    const input = {
      nodeId: 'co2-node',
      type: ObservationType.CO2,
      value: 1300,
      unit: 'ppm',
    } as ObservationInput;
    const persisted = { id: 'observation-id', ...input } as never;
    const alert = { id: 'alert-id' } as never;
    const comfort = {
      spaceId: 'A-1540',
      score: 75,
      status: 'warning' as const,
      values: { temperature: 23, humidity: 45, co2: 1300, noise: 60 },
      components: { temperature: 100, humidity: 100, co2: 40, noise: 80 },
    };
    jest.spyOn(observationService, 'create').mockResolvedValue(persisted);
    jest.spyOn(alertsService, 'evaluate').mockResolvedValue({ created: alert });
    jest.spyOn(analysisService, 'getCurrentComfort').mockResolvedValue(comfort);

    await processor.process(input);

    expect(realtimeGateway.emitAlertCreated).toHaveBeenCalledWith(alert);
    expect(realtimeGateway.emitComfortUpdated).toHaveBeenCalledWith(comfort);
    expect(kafkaProducer.publishAlert).toHaveBeenCalledWith(
      alert,
      expect.objectContaining({ spaceId: undefined, spaceLabel: undefined }),
    );
    expect(kafkaProducer.publishComfort).toHaveBeenCalledWith(
      comfort,
      expect.any(Object),
    );
  });

  it('does not republish an already active alert', async () => {
    const input = {
      nodeId: 'co2-node',
      type: ObservationType.CO2,
      value: 1400,
      unit: 'ppm',
      observedAt: null,
      metadata: null,
    } as ObservationInput;
    const persisted = { id: 'observation-id', ...input } as never;
    jest.spyOn(observationService, 'create').mockResolvedValue(persisted);
    jest.spyOn(alertsService, 'evaluate').mockResolvedValue({});
    jest.spyOn(analysisService, 'getCurrentComfort').mockResolvedValue({
      status: 'unavailable',
      message: 'missing data',
      missingTypes: ['temperature'],
    });

    await processor.process(input);

    expect(kafkaProducer.publishAlert).not.toHaveBeenCalled();
  });

  it('keeps the persisted observation successful when producer calls reject', async () => {
    const input = {
      nodeId: 'co2-node',
      type: ObservationType.CO2,
      value: 1301,
      unit: 'ppm',
      observedAt: null,
      metadata: null,
    } as ObservationInput;
    const persisted = { id: 'observation-id', ...input } as never;
    const alert = { id: 'alert-id' } as never;
    const comfort = {
      spaceId: 'A-1540',
      score: 70,
      status: 'warning' as const,
      values: { temperature: 23, humidity: 45, co2: 1301, noise: 60 },
      components: { temperature: 100, humidity: 100, co2: 40, noise: 80 },
    };
    jest.spyOn(observationService, 'create').mockResolvedValue(persisted);
    jest.spyOn(alertsService, 'evaluate').mockResolvedValue({ created: alert });
    jest.spyOn(analysisService, 'getCurrentComfort').mockResolvedValue(comfort);
    jest
      .spyOn(kafkaProducer, 'publishAlert')
      .mockRejectedValue(new Error('Kafka unavailable'));
    jest
      .spyOn(kafkaProducer, 'publishComfort')
      .mockRejectedValue(new Error('Kafka unavailable'));

    await expect(processor.process(input)).resolves.toBe(persisted);
    expect(observationService.create).toHaveBeenCalledWith(input);
  });

  it('rejects an invalid observation before persistence', async () => {
    const input = {
      nodeId: 'invalid-co2-node',
      type: ObservationType.CO2,
      value: 900,
      unit: 'dBA',
      observedAt: null,
      metadata: null,
    } as ObservationInput;

    await expect(processor.process(input)).rejects.toThrow(
      'unit dBA is invalid for co2',
    );
    expect(observationService.create).not.toHaveBeenCalled();
  });
});
