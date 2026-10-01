import { ConfigService } from '@nestjs/config';

export const KAFKA_TOPICS = [
  'gridd.obs.environmental.temperature',
  'gridd.obs.environmental.humidity',
  'gridd.obs.environmental.co2',
  'gridd.obs.acoustic.sound_level',
  'gridd.obs.occupancy.count',
] as const;

export type KafkaConnectionStatus =
  | 'disabled'
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'error';

export interface KafkaRuntimeConfig {
  enabled: boolean;
  producerEnabled: boolean;
  brokers: string[];
  securityProtocol: string;
  saslMechanism: string;
  username: string;
  password: string;
  caCertPath: string;
  groupId: string;
  reconnectIntervalMs: number;
}

export function loadKafkaConfig(config: ConfigService): KafkaRuntimeConfig {
  const enabled = config.get<string>('KAFKA_ENABLED', 'false').toLowerCase() === 'true';
  const producerEnabled =
    config.get<string>('KAFKA_PRODUCER_ENABLED', 'false').toLowerCase() === 'true';
  const reconnectInterval = Number(
    config.get<string>('KAFKA_RECONNECT_INTERVAL_MS', '5000'),
  );
  const result: KafkaRuntimeConfig = {
    enabled,
    producerEnabled,
    brokers: config
      .get<string>('KAFKA_BROKERS', 'kafka.gridd-dt.ca:9096')
      .split(',')
      .map((broker) => broker.trim())
      .filter(Boolean),
    securityProtocol: config.get<string>('KAFKA_SECURITY_PROTOCOL', 'SASL_SSL'),
    saslMechanism: config.get<string>(
      'KAFKA_SASL_MECHANISM',
      'scram-sha-256',
    ),
    username: config.get<string>('KAFKA_USERNAME', ''),
    password: config.get<string>('KAFKA_PASSWORD', ''),
    caCertPath: config.get<string>('KAFKA_CA_CERT_PATH', ''),
    groupId: config.get<string>(
      'KAFKA_GROUP_ID',
      'gridd-smart-environment-dashboard',
    ),
    reconnectIntervalMs:
      Number.isFinite(reconnectInterval) && reconnectInterval > 0
        ? reconnectInterval
        : 5000,
  };

  if (result.enabled || result.producerEnabled) validateKafkaConfig(result);
  return result;
}

function validateKafkaConfig(config: KafkaRuntimeConfig): void {
  if (config.brokers.length === 0) throw new Error('KAFKA_BROKERS is required');
  if (config.securityProtocol !== 'SASL_SSL') {
    throw new Error('KAFKA_SECURITY_PROTOCOL must be SASL_SSL');
  }
  if (config.saslMechanism !== 'scram-sha-256') {
    throw new Error('KAFKA_SASL_MECHANISM must be scram-sha-256');
  }
  if (!config.username) throw new Error('KAFKA_USERNAME is required');
  if (!config.password) throw new Error('KAFKA_PASSWORD is required');
  if (!config.caCertPath) throw new Error('KAFKA_CA_CERT_PATH is required');
  if (config.enabled && !config.groupId) {
    throw new Error('KAFKA_GROUP_ID is required');
  }
}
