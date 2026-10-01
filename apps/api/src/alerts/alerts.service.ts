import { Inject, Injectable } from '@nestjs/common';
import { ConfigType } from '@nestjs/config';
import { InjectRepository } from '@nestjs/typeorm';
import { IsNull, Not, Repository } from 'typeorm';
import environmentConfig from '../analysis/environment.config';
import {
  Observation,
  ObservationType,
} from '../observations/entities/observation.entity';
import { Alert, AlertSeverity, AlertType } from './entities/alert.entity';

export type AlertFilter = 'active' | 'history' | 'all';

export interface AlertEvaluationResult {
  created?: Alert;
  resolved?: Alert;
}

interface AlertRule {
  type: AlertType;
  threshold: number;
}

@Injectable()
export class AlertsService {
  constructor(
    @InjectRepository(Alert)
    private readonly alertsRepository: Repository<Alert>,
    @Inject(environmentConfig.KEY)
    private readonly config: ConfigType<typeof environmentConfig>,
  ) {}

  find(filter: AlertFilter = 'active'): Promise<Alert[]> {
    if (filter === 'active') {
      return this.alertsRepository.find({
        where: { resolvedAt: IsNull() },
        order: { createdAt: 'DESC' },
      });
    }
    if (filter === 'history') {
      return this.alertsRepository.find({
        where: { resolvedAt: Not(IsNull()) },
        order: { createdAt: 'DESC' },
      });
    }
    return this.alertsRepository.find({ order: { createdAt: 'DESC' } });
  }

  async evaluate(observation: Observation): Promise<AlertEvaluationResult> {
    const rule = this.ruleFor(observation.type);
    if (!rule) return {};

    const active = await this.alertsRepository.findOne({
      where: {
        type: rule.type,
        nodeId: observation.nodeId,
        spaceId: observation.spaceId ?? IsNull(),
        resolvedAt: IsNull(),
      },
    });
    const exceedsThreshold = observation.value > rule.threshold;

    if (!exceedsThreshold) {
      if (!active) return {};
      active.resolvedAt = new Date();
      active.value = observation.value;
      return { resolved: await this.alertsRepository.save(active) };
    }

    const severity = AlertSeverity.CRITICAL;
    const threshold = rule.threshold;

    if (active) {
      active.value = observation.value;
      active.severity = severity;
      active.threshold = threshold;
      await this.alertsRepository.save(active);
      return {};
    }

    const alert = this.alertsRepository.create({
      type: rule.type,
      severity,
      value: observation.value,
      threshold,
      unit: observation.unit,
      nodeId: observation.nodeId,
      spaceId: observation.spaceId,
      resolvedAt: null,
    });

    try {
      return { created: await this.alertsRepository.save(alert) };
    } catch (error) {
      if (this.isUniqueViolation(error)) return {};
      throw error;
    }
  }

  private ruleFor(type: ObservationType): AlertRule | undefined {
    const thresholds = this.config.thresholds;
    switch (type) {
      case ObservationType.CO2:
        return {
          type: AlertType.HIGH_CO2,
          threshold: thresholds.co2.warningMax,
        };
      case ObservationType.SOUND_LEVEL:
        return {
          type: AlertType.HIGH_SOUND_LEVEL,
          threshold: thresholds.soundLevel.warningMax,
        };
      case ObservationType.TEMPERATURE:
        return {
          type: AlertType.HIGH_TEMPERATURE,
          threshold: thresholds.temperature.warningMax,
        };
      default:
        return undefined;
    }
  }

  private isUniqueViolation(error: unknown): boolean {
    return (
      typeof error === 'object' &&
      error !== null &&
      'code' in error &&
      error.code === '23505'
    );
  }
}
