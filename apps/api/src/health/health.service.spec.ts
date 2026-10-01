import { ServiceUnavailableException } from '@nestjs/common';
import { DataSource } from 'typeorm';
import { KafkaConsumerService } from '../kafka/kafka.consumer.service';
import { HealthService } from './health.service';

describe('HealthService', () => {
  const dataSource = { query: jest.fn() } as unknown as DataSource;
  const kafkaConsumer = {
    getStatus: jest.fn().mockReturnValue('disabled'),
  } as unknown as KafkaConsumerService;
  const service = new HealthService(dataSource, kafkaConsumer);

  beforeEach(() => jest.clearAllMocks());

  it('reports a connected database after a successful query', async () => {
    jest.spyOn(dataSource, 'query').mockResolvedValue([{ '?column?': 1 }]);

    await expect(service.check()).resolves.toEqual({
      status: 'ok',
      database: 'connected',
      kafka: 'disabled',
    });
    expect(dataSource.query).toHaveBeenCalledWith('SELECT 1');
  });

  it('reports connected Kafka', async () => {
    jest.spyOn(dataSource, 'query').mockResolvedValue([{ '?column?': 1 }]);
    jest.spyOn(kafkaConsumer, 'getStatus').mockReturnValue('connected');

    await expect(service.check()).resolves.toEqual({
      status: 'ok', database: 'connected', kafka: 'connected',
    });
  });

  it('returns service unavailable when enabled Kafka is unavailable', async () => {
    jest.spyOn(dataSource, 'query').mockResolvedValue([{ '?column?': 1 }]);
    jest.spyOn(kafkaConsumer, 'getStatus').mockReturnValue('error');

    await expect(service.check()).rejects.toMatchObject({
      response: { status: 'error', database: 'connected', kafka: 'error' },
    });
  });

  it('returns service unavailable when PostgreSQL cannot be reached', async () => {
    jest.spyOn(dataSource, 'query').mockRejectedValue(new Error('unavailable'));

    await expect(service.check()).rejects.toBeInstanceOf(
      ServiceUnavailableException,
    );
  });
});
