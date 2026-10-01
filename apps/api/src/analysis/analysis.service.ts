import { Inject, Injectable } from '@nestjs/common';
import { ConfigType } from '@nestjs/config';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import {
  Observation,
  ObservationType,
} from '../observations/entities/observation.entity';
import { ComfortResponse, ComfortResult } from './comfort.types';
import environmentConfig from './environment.config';

const REQUIRED_TYPES = [
  ObservationType.TEMPERATURE,
  ObservationType.HUMIDITY,
  ObservationType.CO2,
  ObservationType.SOUND_LEVEL,
] as const;

@Injectable()
export class AnalysisService {
  constructor(
    @InjectRepository(Observation)
    private readonly observationsRepository: Repository<Observation>,
    @Inject(environmentConfig.KEY)
    private readonly config: ConfigType<typeof environmentConfig>,
  ) {}

  async getCurrentComfort(): Promise<ComfortResponse> {
    const observations = await this.observationsRepository
      .createQueryBuilder('observation')
      .distinctOn(['observation.type'])
      .where('observation.type IN (:...types)', { types: REQUIRED_TYPES })
      .orderBy('observation.type', 'ASC')
      .addOrderBy(
        'COALESCE(observation.observedAt, observation.receivedAt)',
        'DESC',
      )
      .addOrderBy('observation.receivedAt', 'DESC')
      .getMany();

    return this.calculateFromObservations(observations);
  }

  calculateFromObservations(observations: Observation[]): ComfortResponse {
    const byType = new Map(observations.map((item) => [item.type, item]));
    const missingTypes = REQUIRED_TYPES.filter((type) => !byType.has(type));

    if (missingTypes.length > 0) {
      return {
        status: 'unavailable',
        message: 'Comfort index requires temperature, humidity, CO2 and sound level observations.',
        missingTypes,
      };
    }

    const temperature = byType.get(ObservationType.TEMPERATURE)!;
    const humidity = byType.get(ObservationType.HUMIDITY)!;
    const co2 = byType.get(ObservationType.CO2)!;
    const sound = byType.get(ObservationType.SOUND_LEVEL)!;
    const thresholds = this.config.thresholds;
    const components = {
      temperature: this.scoreRange(temperature.value, thresholds.temperature),
      humidity: this.scoreRange(humidity.value, thresholds.humidity),
      co2: this.scoreUpperBound(co2.value, thresholds.co2),
      noise: this.scoreUpperBound(sound.value, thresholds.soundLevel),
    };
    const weights = this.config.weights;
    const totalWeight = Object.values(weights).reduce((sum, weight) => sum + weight, 0);
    const weightedScore =
      components.temperature * weights.temperature +
      components.humidity * weights.humidity +
      components.co2 * weights.co2 +
      components.noise * weights.noise;
    const score = Math.round(weightedScore / (totalWeight || 1));

    return {
      spaceId: temperature.spaceId ?? humidity.spaceId ?? co2.spaceId ?? sound.spaceId,
      score,
      status: this.statusFor(score),
      components,
    } satisfies ComfortResult;
  }

  private scoreRange(
    value: number,
    threshold: {
      warningMin: number;
      normalMin: number;
      normalMax: number;
      warningMax: number;
    },
  ): number {
    if (value >= threshold.normalMin && value <= threshold.normalMax) return 100;
    if (value >= threshold.warningMin && value < threshold.normalMin) {
      return this.interpolate(value, threshold.warningMin, threshold.normalMin, 60, 100);
    }
    if (value > threshold.normalMax && value <= threshold.warningMax) {
      return this.interpolate(value, threshold.normalMax, threshold.warningMax, 100, 60);
    }
    if (value < threshold.warningMin) {
      const span = threshold.normalMin - threshold.warningMin;
      return this.clamp(60 - ((threshold.warningMin - value) / span) * 60);
    }
    const span = threshold.warningMax - threshold.normalMax;
    return this.clamp(60 - ((value - threshold.warningMax) / span) * 60);
  }

  private scoreUpperBound(
    value: number,
    threshold: { normalMax: number; warningMax: number },
  ): number {
    if (value <= threshold.normalMax) return 100;
    const span = threshold.warningMax - threshold.normalMax;
    if (value <= threshold.warningMax) {
      return this.interpolate(value, threshold.normalMax, threshold.warningMax, 100, 60);
    }
    return this.clamp(60 - ((value - threshold.warningMax) / span) * 60);
  }

  private statusFor(score: number): ComfortResult['status'] {
    if (score >= this.config.status.goodMin) return 'good';
    if (score >= this.config.status.warningMin) return 'warning';
    return 'critical';
  }

  private interpolate(
    value: number,
    start: number,
    end: number,
    startScore: number,
    endScore: number,
  ): number {
    const ratio = (value - start) / (end - start);
    return this.clamp(startScore + ratio * (endScore - startScore));
  }

  private clamp(value: number): number {
    return Math.round(Math.min(100, Math.max(0, value)));
  }
}
