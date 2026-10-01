import {
  Injectable,
  Logger,
  OnModuleDestroy,
  OnModuleInit,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import {
  Observation,
  ObservationType,
} from '../observations/entities/observation.entity';
import { ObservationInput } from '../observations/interfaces/observation-input.interface';
import { ObservationProcessor } from '../observations/observation.processor';

interface SimulationDefinition {
  type: ObservationType;
  unit: string;
  min: number;
  max: number;
  decimals: number;
  position: { x: number; y: number; z: number };
}

const DEFINITIONS: readonly SimulationDefinition[] = [
  { type: ObservationType.TEMPERATURE, unit: '°C', min: 18, max: 30, decimals: 1, position: { x: 2.1, y: 1.4, z: 1.5 } },
  { type: ObservationType.HUMIDITY, unit: '%', min: 20, max: 75, decimals: 1, position: { x: 2.1, y: 1.4, z: 1.5 } },
  { type: ObservationType.CO2, unit: 'ppm', min: 400, max: 1600, decimals: 0, position: { x: 4.2, y: 2.8, z: 1.5 } },
  { type: ObservationType.SOUND_LEVEL, unit: 'dBA', min: 30, max: 80, decimals: 1, position: { x: 5.7, y: 3.2, z: 1.5 } },
  { type: ObservationType.OCCUPANCY, unit: 'person', min: 0, max: 25, decimals: 0, position: { x: 1.0, y: 0.5, z: 2.4 } },
];

@Injectable()
export class SimulatorService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(SimulatorService.name);
  private timer?: NodeJS.Timeout;
  private generationInProgress = false;

  constructor(
    private readonly configService: ConfigService,
    private readonly observationProcessor: ObservationProcessor,
  ) {}

  onModuleInit(): void {
    if (!this.isEnabled()) {
      this.logger.log('Observation simulator is disabled');
      return;
    }

    const intervalMs = this.getIntervalMs();
    this.logger.log(`Observation simulator enabled (${intervalMs} ms)`);
    void this.runScheduledGeneration();
    this.timer = setInterval(() => {
      void this.runScheduledGeneration();
    }, intervalMs);
  }

  onModuleDestroy(): void {
    if (this.timer) {
      clearInterval(this.timer);
    }
  }

  generateOnce(): Promise<Observation[]> {
    const observedAt = new Date();
    return Promise.all(
      DEFINITIONS.map((definition) =>
        this.observationProcessor.process(
          this.createObservation(definition, observedAt),
        ),
      ),
    );
  }

  private async runScheduledGeneration(): Promise<void> {
    if (this.generationInProgress) {
      return;
    }

    this.generationInProgress = true;
    try {
      await this.generateOnce();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.logger.error(`Failed to generate observations: ${message}`);
    } finally {
      this.generationInProgress = false;
    }
  }

  private isEnabled(): boolean {
    return (
      this.configService.get<string>('SIMULATOR_ENABLED', 'false').toLowerCase() ===
      'true'
    );
  }

  private getIntervalMs(): number {
    const configured = Number(
      this.configService.get<string>('SIMULATOR_INTERVAL_MS', '5000'),
    );
    return Number.isFinite(configured) && configured > 0 ? configured : 5000;
  }

  private createObservation(
    definition: SimulationDefinition,
    observedAt: Date,
  ): ObservationInput {
    const { x, y, z } = definition.position;
    return {
      nodeId: `simulator-${definition.type}-A-1540`,
      type: definition.type,
      value: this.randomValue(definition),
      unit: definition.unit,
      observedAt,
      siteId: 'ets',
      siteLabel: 'École de technologie supérieure',
      buildingId: 'A',
      buildingLabel: 'Pavillon A',
      storeyId: '1',
      storeyLabel: '1er étage',
      spaceId: 'A-1540',
      spaceLabel: 'GRIDD',
      zoneId: 'professors-office',
      zoneLabel: 'Bureau des professeurs',
      positionX: x,
      positionY: y,
      positionZ: z,
      metadata: {
        source: 'simulator',
        site: { id: 'ets', label: 'École de technologie supérieure' },
        building: { id: 'A', label: 'Pavillon A' },
        storey: { id: '1', label: '1er étage' },
        space: { id: 'A-1540', label: 'GRIDD', type: 'laboratory' },
        zone: { id: 'professors-office', label: 'Bureau des professeurs' },
        position: { x, y, z, unit: 'm', coordinateSystem: 'A-1540-local' },
      },
    };
  }

  private randomValue(definition: SimulationDefinition): number {
    const value = definition.min + Math.random() * (definition.max - definition.min);
    return Number(value.toFixed(definition.decimals));
  }
}
