import { readFileSync } from 'node:fs';
import { Kafka, logLevel } from 'kafkajs';
import { KafkaRuntimeConfig } from './kafka.config';

export function createKafkaClient(config: KafkaRuntimeConfig): Kafka {
  const ca = readFileSync(config.caCertPath, 'utf8');
  return new Kafka({
    clientId: 'gridd-smart-environment-api',
    brokers: config.brokers,
    ssl: { ca: [ca], rejectUnauthorized: true },
    sasl: {
      mechanism: 'scram-sha-256',
      username: config.username,
      password: config.password,
    },
    logLevel: logLevel.WARN,
    retry: { retries: 8 },
  });
}
