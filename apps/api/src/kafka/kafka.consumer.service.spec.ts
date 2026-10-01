import { ConfigService } from '@nestjs/config';
import { Consumer, KafkaMessage } from 'kafkajs';
import { ObservationProcessor } from '../observations/observation.processor';
import { KafkaConsumerFactory } from './kafka.consumer.factory';
import { KafkaConsumerService } from './kafka.consumer.service';

describe('KafkaConsumerService', () => {
  const processor = { process: jest.fn() } as unknown as ObservationProcessor;

  beforeEach(() => jest.clearAllMocks());

  it('does not create or connect a consumer when Kafka is disabled', () => {
    const factory = jest.fn() as KafkaConsumerFactory;
    const service = new KafkaConsumerService(
      new ConfigService({ KAFKA_ENABLED: 'false' }),
      processor,
      factory,
    );

    service.onModuleInit();

    expect(service.getStatus()).toBe('disabled');
    expect(factory).not.toHaveBeenCalled();
  });

  it('passes a valid mapped observation to ObservationProcessor', async () => {
    jest.spyOn(processor, 'process').mockResolvedValue({} as never);
    const service = disabledService();
    const kafkaMessage = {
      value: Buffer.from(JSON.stringify({
        node_id: 'gridd-temperature-1',
        type: 'temperature',
        value: 24.2,
        unit: '°C',
        metadata: { space: { id: 'A-1540', label: 'GRIDD' } },
      })),
      offset: '12',
    } as KafkaMessage;

    await expect(service.handleMessage(
      'gridd.obs.environmental.temperature', kafkaMessage, 2,
    )).resolves.toBe(true);
    expect(processor.process).toHaveBeenCalledWith(expect.objectContaining({
      nodeId: 'gridd-temperature-1',
      type: 'temperature',
      value: 24.2,
      spaceId: 'A-1540',
    }));
  });

  it('logs and skips invalid messages without calling the pipeline', async () => {
    const service = disabledService();
    const kafkaMessage = { value: Buffer.from('{'), offset: '13' } as KafkaMessage;

    await expect(service.handleMessage(
      'gridd.obs.environmental.temperature', kafkaMessage,
    )).resolves.toBe(false);
    expect(processor.process).not.toHaveBeenCalled();
  });

  it('propagates pipeline failures so the offset is not silently committed', async () => {
    jest.spyOn(processor, 'process').mockRejectedValue(new Error('database down'));
    const service = disabledService();
    const kafkaMessage = {
      value: Buffer.from(JSON.stringify({
        node_id: 'n1', type: 'co2', value: 700, unit: 'ppm',
      })),
      offset: '14',
    } as KafkaMessage;

    await expect(service.handleMessage(
      'gridd.obs.environmental.co2', kafkaMessage,
    )).rejects.toThrow('database down');
  });

  it('reports an initial Kafka connection error without crashing NestJS', async () => {
    const consumer = {
      events: { CONNECT: 'connect', DISCONNECT: 'disconnect', CRASH: 'crash' },
      on: jest.fn(),
      connect: jest.fn().mockRejectedValue(new Error('broker unavailable')),
      disconnect: jest.fn().mockResolvedValue(undefined),
      subscribe: jest.fn(),
      run: jest.fn(),
    } as unknown as Consumer;
    const config = new ConfigService({
      KAFKA_ENABLED: 'true',
      KAFKA_USERNAME: 'user',
      KAFKA_PASSWORD: 'secret',
      KAFKA_CA_CERT_PATH: 'ca.pem',
      KAFKA_RECONNECT_INTERVAL_MS: '60000',
    });
    const service = new KafkaConsumerService(config, processor, () => consumer);

    service.onModuleInit();
    await new Promise((resolve) => setImmediate(resolve));

    expect(service.getStatus()).toBe('error');
    await service.onModuleDestroy();
  });

  it('connects, subscribes to all topics and starts consuming', async () => {
    const consumer = {
      events: { CONNECT: 'connect', DISCONNECT: 'disconnect', CRASH: 'crash' },
      on: jest.fn(),
      connect: jest.fn().mockResolvedValue(undefined),
      disconnect: jest.fn().mockResolvedValue(undefined),
      subscribe: jest.fn().mockResolvedValue(undefined),
      run: jest.fn().mockResolvedValue(undefined),
    } as unknown as Consumer;
    const config = new ConfigService({
      KAFKA_ENABLED: 'true',
      KAFKA_USERNAME: 'user',
      KAFKA_PASSWORD: 'secret',
      KAFKA_CA_CERT_PATH: 'ca.pem',
    });
    const service = new KafkaConsumerService(config, processor, () => consumer);

    service.onModuleInit();
    await new Promise((resolve) => setImmediate(resolve));

    expect(service.getStatus()).toBe('connected');
    expect(consumer.connect).toHaveBeenCalled();
    expect(consumer.subscribe).toHaveBeenCalledWith({
      topics: [
        'gridd.obs.environmental.temperature',
        'gridd.obs.environmental.humidity',
        'gridd.obs.environmental.co2',
        'gridd.obs.acoustic.sound_level',
        'gridd.obs.occupancy.count',
      ],
      fromBeginning: false,
    });
    expect(consumer.run).toHaveBeenCalled();
    await service.onModuleDestroy();
  });

  function disabledService(): KafkaConsumerService {
    return new KafkaConsumerService(
      new ConfigService({ KAFKA_ENABLED: 'false' }),
      processor,
      jest.fn() as KafkaConsumerFactory,
    );
  }
});
