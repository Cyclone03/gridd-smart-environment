import { readFileSync } from 'node:fs';
import { Consumer, Kafka, logLevel } from 'kafkajs';
import { KafkaRuntimeConfig } from './kafka.config';

export const KAFKA_CONSUMER_FACTORY = Symbol('KAFKA_CONSUMER_FACTORY');

export type KafkaConsumerFactory = (config: KafkaRuntimeConfig) => Consumer;

export const kafkaConsumerFactory: KafkaConsumerFactory = (config) => {
  const ca = readFileSync(config.caCertPath, 'utf8');
  const kafka = new Kafka({
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
  return kafka.consumer({ groupId: config.groupId });
};
