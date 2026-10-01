import { ServiceUnavailableException } from '@nestjs/common';
import { DataSource } from 'typeorm';
import { HealthService } from './health.service';

describe('HealthService', () => {
  const dataSource = { query: jest.fn() } as unknown as DataSource;
  const service = new HealthService(dataSource);

  beforeEach(() => jest.clearAllMocks());

  it('reports a connected database after a successful query', async () => {
    jest.spyOn(dataSource, 'query').mockResolvedValue([{ '?column?': 1 }]);

    await expect(service.check()).resolves.toEqual({
      status: 'ok',
      database: 'connected',
    });
    expect(dataSource.query).toHaveBeenCalledWith('SELECT 1');
  });

  it('returns service unavailable when PostgreSQL cannot be reached', async () => {
    jest.spyOn(dataSource, 'query').mockRejectedValue(new Error('unavailable'));

    await expect(service.check()).rejects.toBeInstanceOf(
      ServiceUnavailableException,
    );
  });
});
