import { Injectable, ServiceUnavailableException } from '@nestjs/common';
import { DataSource } from 'typeorm';
import { KafkaConsumerService } from '../kafka/kafka.consumer.service';
import { KafkaConnectionStatus } from '../kafka/kafka.config';

export interface HealthStatus {
  status: 'ok' | 'error';
  database: 'connected';
  kafka: KafkaConnectionStatus;
}

@Injectable()
export class HealthService {
  constructor(
    private readonly dataSource: DataSource,
    private readonly kafkaConsumer: KafkaConsumerService,
  ) {}

  async check(): Promise<HealthStatus> {
    try {
      await this.dataSource.query('SELECT 1');
      const kafka = this.kafkaConsumer.getStatus();
      if (kafka !== 'disabled' && kafka !== 'connected') {
        throw new ServiceUnavailableException({
          status: 'error',
          database: 'connected',
          kafka,
        });
      }
      return { status: 'ok', database: 'connected', kafka };
    } catch (error) {
      if (error instanceof ServiceUnavailableException) throw error;
      throw new ServiceUnavailableException({
        status: 'error',
        database: 'disconnected',
        kafka: this.kafkaConsumer.getStatus(),
      });
    }
  }
}
