import { forwardRef, Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AnalysisModule } from '../analysis/analysis.module';
import { AlertsModule } from '../alerts/alerts.module';
import { RealtimeModule } from '../realtime/realtime.module';
import { KafkaModule } from '../kafka/kafka.module';
import { Observation } from './entities/observation.entity';
import { ObservationProcessor } from './observation.processor';
import { ObservationsController } from './observations.controller';
import { ObservationService } from './observations.service';

@Module({
  imports: [
    TypeOrmModule.forFeature([Observation]),
    AnalysisModule,
    AlertsModule,
    RealtimeModule,
    forwardRef(() => KafkaModule),
  ],
  controllers: [ObservationsController],
  providers: [ObservationService, ObservationProcessor],
  exports: [ObservationService, ObservationProcessor],
})
export class ObservationsModule {}
