import { Consumer } from 'kafkajs';
import { createKafkaClient } from './kafka.client.factory';
import { KafkaRuntimeConfig } from './kafka.config';

export const KAFKA_CONSUMER_FACTORY = Symbol('KAFKA_CONSUMER_FACTORY');

export type KafkaConsumerFactory = (config: KafkaRuntimeConfig) => Consumer;

export const kafkaConsumerFactory: KafkaConsumerFactory = (config) => {
  return createKafkaClient(config).consumer({ groupId: config.groupId });
};
