import {
  Inject,
  Injectable,
  Logger,
  OnModuleDestroy,
  OnModuleInit,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Consumer, KafkaMessage } from 'kafkajs';
import { ObservationProcessor } from '../observations/observation.processor';
import { InvalidObservationError } from '../observations/observation-input.validator';
import {
  KafkaConnectionStatus,
  KAFKA_TOPICS,
  KafkaRuntimeConfig,
  loadKafkaConfig,
} from './kafka.config';
import {
  KAFKA_CONSUMER_FACTORY,
  KafkaConsumerFactory,
} from './kafka.consumer.factory';
import {
  InvalidKafkaObservationError,
  mapKafkaObservation,
} from './kafka-message.mapper';

@Injectable()
export class KafkaConsumerService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(KafkaConsumerService.name);
  private consumer?: Consumer;
  private config?: KafkaRuntimeConfig;
  private status: KafkaConnectionStatus = 'disabled';
  private reconnectTimer?: NodeJS.Timeout;
  private starting = false;
  private shuttingDown = false;

  constructor(
    private readonly configService: ConfigService,
    private readonly observationProcessor: ObservationProcessor,
    @Inject(KAFKA_CONSUMER_FACTORY)
    private readonly consumerFactory: KafkaConsumerFactory,
  ) {}

  onModuleInit(): void {
    try {
      this.config = loadKafkaConfig(this.configService);
    } catch (error) {
      this.status = 'error';
      this.logger.error(this.errorMessage('Invalid Kafka configuration', error));
      return;
    }
    if (!this.config.enabled) {
      this.status = 'disabled';
      this.logger.log('Kafka consumer is disabled');
      return;
    }
    if (
      this.configService.get<string>('SIMULATOR_ENABLED', 'false').toLowerCase() ===
      'true'
    ) {
      this.logger.warn(
        'Kafka and the observation simulator are both enabled; observations will come from both sources',
      );
    }
    void this.connect();
  }

  async onModuleDestroy(): Promise<void> {
    this.shuttingDown = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.consumer) {
      try {
        await this.consumer.disconnect();
      } catch (error) {
        this.logger.error(this.errorMessage('Kafka disconnect failed', error));
      }
    }
    if (this.status !== 'disabled') this.status = 'disconnected';
  }

  getStatus(): KafkaConnectionStatus {
    return this.status;
  }

  async handleMessage(
    topic: string,
    message: KafkaMessage,
    partition = 0,
  ): Promise<boolean> {
    try {
      const input = mapKafkaObservation(topic, message.value);
      await this.observationProcessor.process(input);
      this.logger.log(
        JSON.stringify({
          event: 'kafka_observation_processed',
          topic,
          partition,
          offset: message.offset,
          nodeId: input.nodeId,
          type: input.type,
        }),
      );
      return true;
    } catch (error) {
      if (
        error instanceof InvalidKafkaObservationError ||
        error instanceof InvalidObservationError
      ) {
        this.logger.warn(
          JSON.stringify({
            event: 'kafka_observation_rejected',
            topic,
            partition,
            offset: message.offset,
            reason: error.message,
          }),
        );
        return false;
      }
      this.logger.error(
        this.errorMessage(
          `Kafka observation pipeline failed topic=${topic} partition=${partition} offset=${message.offset}`,
          error,
        ),
      );
      throw error;
    }
  }

  private async connect(): Promise<void> {
    if (!this.config?.enabled || this.starting || this.shuttingDown) return;
    this.starting = true;
    this.status = 'connecting';
    try {
      const consumer = this.consumerFactory(this.config);
      this.consumer = consumer;
      consumer.on(consumer.events.CONNECT, () => {
        this.status = 'connected';
        this.logger.log('Kafka consumer connected');
      });
      consumer.on(consumer.events.DISCONNECT, () => {
        if (!this.shuttingDown) this.status = 'disconnected';
        this.logger.warn('Kafka consumer disconnected');
      });
      consumer.on(consumer.events.CRASH, ({ payload }) => {
        this.status = 'error';
        this.logger.error(
          this.errorMessage('Kafka consumer crashed', payload.error),
        );
      });

      await consumer.connect();
      await consumer.subscribe({ topics: [...KAFKA_TOPICS], fromBeginning: false });
      await consumer.run({
        eachMessage: async ({ topic, partition, message }) => {
          await this.handleMessage(topic, message, partition);
        },
      });
      this.status = 'connected';
    } catch (error) {
      this.status = 'error';
      this.logger.error(this.errorMessage('Kafka connection failed', error));
      await this.disconnectAfterFailure();
      this.scheduleReconnect();
    } finally {
      this.starting = false;
    }
  }

  private async disconnectAfterFailure(): Promise<void> {
    if (!this.consumer) return;
    try {
      await this.consumer.disconnect();
    } catch {
      // The original connection error is the actionable failure.
    } finally {
      this.consumer = undefined;
    }
  }

  private scheduleReconnect(): void {
    if (this.shuttingDown || !this.config?.enabled || this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = undefined;
      void this.connect();
    }, this.config.reconnectIntervalMs);
  }

  private errorMessage(context: string, error: unknown): string {
    const message = error instanceof Error ? error.message : String(error);
    return JSON.stringify({ event: 'kafka_error', context, message });
  }
}
