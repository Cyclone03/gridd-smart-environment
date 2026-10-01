import { ConfigService } from '@nestjs/config';
import { loadKafkaConfig } from './kafka.config';

describe('Kafka configuration', () => {
  it('is disabled by default without requiring credentials', () => {
    expect(loadKafkaConfig(new ConfigService())).toMatchObject({
      enabled: false,
      brokers: ['kafka.gridd-dt.ca:9096'],
      securityProtocol: 'SASL_SSL',
      saslMechanism: 'scram-sha-256',
      groupId: 'gridd-smart-environment-dashboard',
    });
  });

  it('loads a valid TLS and SASL configuration', () => {
    const config = loadKafkaConfig(
      new ConfigService({
        KAFKA_ENABLED: 'true',
        KAFKA_BROKERS: 'broker-a:9096, broker-b:9096',
        KAFKA_SECURITY_PROTOCOL: 'SASL_SSL',
        KAFKA_SASL_MECHANISM: 'scram-sha-256',
        KAFKA_USERNAME: 'user',
        KAFKA_PASSWORD: 'secret',
        KAFKA_CA_CERT_PATH: '/certs/ca.pem',
        KAFKA_GROUP_ID: 'stable-group',
      }),
    );

    expect(config).toMatchObject({
      enabled: true,
      brokers: ['broker-a:9096', 'broker-b:9096'],
      username: 'user',
      caCertPath: '/certs/ca.pem',
      groupId: 'stable-group',
    });
  });

  it.each([
    ['KAFKA_USERNAME', ''],
    ['KAFKA_PASSWORD', ''],
    ['KAFKA_CA_CERT_PATH', ''],
  ])('rejects enabled Kafka when %s is missing', (key, value) => {
    const environment: Record<string, string> = {
      KAFKA_ENABLED: 'true',
      KAFKA_USERNAME: 'user',
      KAFKA_PASSWORD: 'secret',
      KAFKA_CA_CERT_PATH: '/certs/ca.pem',
      [key]: value,
    };

    expect(() => loadKafkaConfig(new ConfigService(environment))).toThrow(key);
  });
});
