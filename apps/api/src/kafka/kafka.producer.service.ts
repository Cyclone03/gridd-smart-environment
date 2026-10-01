import {
  Inject,
  Injectable,
  Logger,
  OnModuleDestroy,
  OnModuleInit,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Producer } from 'kafkajs';
import { ComfortResult } from '../analysis/comfort.types';
import { Alert, AlertType } from '../alerts/entities/alert.entity';
import {
  KafkaConnectionStatus,
  KafkaRuntimeConfig,
  loadKafkaConfig,
} from './kafka.config';
import {
  KAFKA_PRODUCER_FACTORY,
  KafkaProducerFactory,
} from './kafka.producer.factory';

export const COMFORT_TOPIC = 'gridd.derived.environmental.thermal_comfort';

export const ALERT_TOPICS: Readonly<Record<AlertType, string>> = {
  [AlertType.HIGH_CO2]: 'gridd.alert.environmental.high_co2',
  [AlertType.HIGH_TEMPERATURE]: 'gridd.alert.environmental.high_temperature',
  [AlertType.HIGH_SOUND_LEVEL]: 'gridd.alert.acoustic.high_sound_level',
};

export interface KafkaPublicationContext {
  spaceId: string | null;
  spaceLabel: string | null;
  timestamp: Date;
}

interface PublishedMetadata {
  space: { id: string | null; label: string | null };
}

export interface ThermalComfortPayload {
  type: 'thermal_comfort';
  value: number;
  unit: 'score';
  status: ComfortResult['status'];
  components: ComfortResult['components'];
  timestamp: string;
  metadata: PublishedMetadata;
}

export interface AlertPayload {
  type: 'high_co2' | 'high_temperature' | 'high_sound_level';
  value: number;
  unit: string;
  threshold: number;
  severity: string;
  timestamp: string;
  metadata: PublishedMetadata;
}

@Injectable()
export class KafkaProducerService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(KafkaProducerService.name);
  private producer?: Producer;
  private config?: KafkaRuntimeConfig;
  private status: KafkaConnectionStatus = 'disabled';
  private connection?: Promise<boolean>;
  private reconnectTimer?: NodeJS.Timeout;
  private shuttingDown = false;
  private readonly pending = new Set<Promise<boolean>>();

  constructor(
    private readonly configService: ConfigService,
    @Inject(KAFKA_PRODUCER_FACTORY)
    private readonly producerFactory: KafkaProducerFactory,
  ) {}

  onModuleInit(): void {
    try {
      this.config = loadKafkaConfig(this.configService);
    } catch (error) {
      this.status = 'error';
      this.logger.error(this.errorMessage('Invalid Kafka producer configuration', error));
      return;
    }
    if (!this.config.producerEnabled) {
      this.status = 'disabled';
      this.logger.log('Kafka producer is disabled');
      return;
    }
    void this.connect();
  }

  async onModuleDestroy(): Promise<void> {
    this.shuttingDown = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    await Promise.allSettled([...this.pending]);
    if (this.producer) {
      try {
        await this.producer.disconnect();
      } catch (error) {
        this.logger.error(this.errorMessage('Kafka producer disconnect failed', error));
      }
    }
    if (this.status !== 'disabled') this.status = 'disconnected';
  }

  getStatus(): KafkaConnectionStatus {
    return this.status;
  }

  publishComfort(
    comfort: ComfortResult,
    context: KafkaPublicationContext,
  ): Promise<boolean> {
    const payload: ThermalComfortPayload = {
      type: 'thermal_comfort',
      value: comfort.score,
      unit: 'score',
      status: comfort.status,
      components: comfort.components,
      timestamp: context.timestamp.toISOString(),
      metadata: this.metadata(context),
    };
    return this.track(this.publish(COMFORT_TOPIC, context.spaceId, payload));
  }

  publishAlert(
    alert: Alert,
    context: KafkaPublicationContext,
  ): Promise<boolean> {
    const payload: AlertPayload = {
      type: alert.type.toLowerCase() as AlertPayload['type'],
      value: alert.value,
      unit: alert.unit,
      threshold: alert.threshold,
      severity: alert.severity,
      timestamp: (alert.createdAt ?? context.timestamp).toISOString(),
      metadata: this.metadata(context),
    };
    return this.track(
      this.publish(ALERT_TOPICS[alert.type], context.spaceId ?? alert.nodeId, payload),
    );
  }

  private async publish(
    topic: string,
    key: string | null,
    payload: ThermalComfortPayload | AlertPayload,
  ): Promise<boolean> {
    if (!this.config?.producerEnabled || this.shuttingDown) return false;
    try {
      if (!(await this.connect()) || !this.producer) return false;
      await this.producer.send({
        topic,
        messages: [{ key: key ?? undefined, value: JSON.stringify(payload) }],
      });
      this.logger.log(JSON.stringify({ event: 'kafka_event_published', topic }));
      return true;
    } catch (error) {
      this.status = 'error';
      this.logger.error(this.errorMessage(`Kafka publication failed topic=${topic}`, error));
      this.scheduleReconnect();
      return false;
    }
  }

  private connect(): Promise<boolean> {
    if (!this.config?.producerEnabled || this.shuttingDown) {
      return Promise.resolve(false);
    }
    if (this.status === 'connected' && this.producer) return Promise.resolve(true);
    if (this.connection) return this.connection;
    this.connection = this.doConnect().finally(() => {
      this.connection = undefined;
    });
    return this.connection;
  }

  private async doConnect(): Promise<boolean> {
    this.status = 'connecting';
    try {
      this.producer ??= this.producerFactory(this.config!);
      await this.producer.connect();
      this.status = 'connected';
      this.logger.log('Kafka producer connected');
      return true;
    } catch (error) {
      this.status = 'error';
      this.logger.error(this.errorMessage('Kafka producer connection failed', error));
      this.scheduleReconnect();
      return false;
    }
  }

  private scheduleReconnect(): void {
    if (this.shuttingDown || !this.config?.producerEnabled || this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = undefined;
      void this.connect();
    }, this.config.reconnectIntervalMs);
  }

  private track(publication: Promise<boolean>): Promise<boolean> {
    this.pending.add(publication);
    void publication.finally(() => this.pending.delete(publication));
    return publication;
  }

  private metadata(context: KafkaPublicationContext): PublishedMetadata {
    return {
      space: { id: context.spaceId, label: context.spaceLabel },
    };
  }

  private errorMessage(context: string, error: unknown): string {
    const message = error instanceof Error ? error.message : String(error);
    return JSON.stringify({ event: 'kafka_producer_error', context, message });
  }
}
