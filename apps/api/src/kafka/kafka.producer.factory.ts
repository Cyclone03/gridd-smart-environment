import { Producer } from 'kafkajs';
import { createKafkaClient } from './kafka.client.factory';
import { KafkaRuntimeConfig } from './kafka.config';

export const KAFKA_PRODUCER_FACTORY = Symbol('KAFKA_PRODUCER_FACTORY');

export type KafkaProducerFactory = (config: KafkaRuntimeConfig) => Producer;

export const kafkaProducerFactory: KafkaProducerFactory = (config) =>
  createKafkaClient(config).producer({ allowAutoTopicCreation: false });
