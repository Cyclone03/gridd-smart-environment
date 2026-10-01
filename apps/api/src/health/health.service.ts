import { Injectable, ServiceUnavailableException } from '@nestjs/common';
import { DataSource } from 'typeorm';

export interface HealthStatus {
  status: 'ok';
  database: 'connected';
}

@Injectable()
export class HealthService {
  constructor(private readonly dataSource: DataSource) {}

  async check(): Promise<HealthStatus> {
    try {
      await this.dataSource.query('SELECT 1');
      return { status: 'ok', database: 'connected' };
    } catch {
      throw new ServiceUnavailableException({
        status: 'error',
        database: 'disconnected',
      });
    }
  }
}
