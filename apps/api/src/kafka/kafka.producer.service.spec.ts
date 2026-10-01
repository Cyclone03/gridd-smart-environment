import { ConfigService } from '@nestjs/config';
import { Producer } from 'kafkajs';
import { ComfortResult } from '../analysis/comfort.types';
import {
  Alert,
  AlertSeverity,
  AlertType,
} from '../alerts/entities/alert.entity';
import { KafkaProducerFactory } from './kafka.producer.factory';
import {
  ALERT_TOPICS,
  COMFORT_TOPIC,
  KafkaProducerService,
} from './kafka.producer.service';

describe('KafkaProducerService', () => {
  let producer: {
    connect: jest.Mock;
    disconnect: jest.Mock;
    send: jest.Mock;
  };

  beforeEach(() => {
    producer = {
      connect: jest.fn().mockResolvedValue(undefined),
      disconnect: jest.fn().mockResolvedValue(undefined),
      send: jest.fn().mockResolvedValue([]),
    };
  });

  it('does not create, connect or send when the producer is disabled', async () => {
    const factory = jest.fn() as KafkaProducerFactory;
    const service = new KafkaProducerService(
      new ConfigService({ KAFKA_PRODUCER_ENABLED: 'false' }),
      factory,
    );

    service.onModuleInit();
    await expect(service.publishComfort(comfort(), context())).resolves.toBe(false);

    expect(service.getStatus()).toBe('disabled');
    expect(factory).not.toHaveBeenCalled();
  });

  it('connects and publishes the exact thermal comfort payload', async () => {
    const service = enabledService();
    service.onModuleInit();
    await flushPromises();

    await expect(service.publishComfort(comfort(), context())).resolves.toBe(true);

    expect(producer.connect).toHaveBeenCalledTimes(1);
    expect(producer.send).toHaveBeenCalledWith({
      topic: COMFORT_TOPIC,
      messages: [{
        key: 'A-1540',
        value: JSON.stringify({
          type: 'thermal_comfort',
          value: 87,
          unit: 'score',
          status: 'good',
          components: { temperature: 100, humidity: 100, co2: 70, noise: 80 },
          timestamp: '2026-10-01T12:00:00.000Z',
          metadata: { space: { id: 'A-1540', label: 'GRIDD' } },
        }),
      }],
    });
    await service.onModuleDestroy();
  });

  it.each([
    [AlertType.HIGH_CO2, 'gridd.alert.environmental.high_co2', 'high_co2', 1450, 'ppm', 1200],
    [AlertType.HIGH_TEMPERATURE, 'gridd.alert.environmental.high_temperature', 'high_temperature', 29, '°C', 28],
    [AlertType.HIGH_SOUND_LEVEL, 'gridd.alert.acoustic.high_sound_level', 'high_sound_level', 75, 'dBA', 70],
  ])(
    'publishes %s on its mapped topic',
    async (type, topic, payloadType, value, unit, threshold) => {
      const service = enabledService();
      service.onModuleInit();
      await flushPromises();

      await expect(
        service.publishAlert(alert(type, value, unit, threshold), context()),
      ).resolves.toBe(true);

      expect(ALERT_TOPICS[type]).toBe(topic);
      const request = producer.send.mock.calls[0][0];
      expect(request.topic).toBe(topic);
      expect(JSON.parse(request.messages[0].value)).toEqual({
        type: payloadType,
        value,
        unit,
        threshold,
        severity: 'critical',
        timestamp: '2026-10-01T12:00:00.000Z',
        metadata: { space: { id: 'A-1540', label: 'GRIDD' } },
      });
      await service.onModuleDestroy();
    },
  );

  it('contains publication errors and keeps them non-throwing', async () => {
    producer.send.mockRejectedValue(new Error('broker unavailable'));
    const service = enabledService();
    service.onModuleInit();
    await flushPromises();

    await expect(service.publishComfort(comfort(), context())).resolves.toBe(false);
    expect(service.getStatus()).toBe('error');
    await service.onModuleDestroy();
  });

  it('waits for publications and disconnects during shutdown', async () => {
    const service = enabledService();
    service.onModuleInit();
    await flushPromises();
    const publication = service.publishComfort(comfort(), context());

    await service.onModuleDestroy();
    await publication;

    expect(producer.disconnect).toHaveBeenCalledTimes(1);
    expect(service.getStatus()).toBe('disconnected');
  });

  function enabledService(): KafkaProducerService {
    const config = new ConfigService({
      KAFKA_PRODUCER_ENABLED: 'true',
      KAFKA_USERNAME: 'user',
      KAFKA_PASSWORD: 'secret',
      KAFKA_CA_CERT_PATH: 'ca.pem',
      KAFKA_RECONNECT_INTERVAL_MS: '60000',
    });
    return new KafkaProducerService(
      config,
      () => producer as unknown as Producer,
    );
  }
});

function comfort(): ComfortResult {
  return {
    spaceId: 'A-1540',
    score: 87,
    status: 'good',
    values: { temperature: 23, humidity: 45, co2: 900, noise: 60 },
    components: { temperature: 100, humidity: 100, co2: 70, noise: 80 },
  };
}

function alert(
  type: AlertType,
  value: number,
  unit: string,
  threshold: number,
): Alert {
  return {
    id: 'alert-id',
    type,
    value,
    unit,
    threshold,
    severity: AlertSeverity.CRITICAL,
    nodeId: 'node-1',
    spaceId: 'A-1540',
    createdAt: new Date('2026-10-01T12:00:00.000Z'),
    resolvedAt: null,
  };
}

function context() {
  return {
    spaceId: 'A-1540',
    spaceLabel: 'GRIDD',
    timestamp: new Date('2026-10-01T12:00:00.000Z'),
  };
}

function flushPromises(): Promise<void> {
  return new Promise((resolve) => setImmediate(resolve));
}
