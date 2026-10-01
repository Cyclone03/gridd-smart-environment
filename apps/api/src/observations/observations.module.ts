import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Observation } from './entities/observation.entity';
import { ObservationsController } from './observations.controller';
import { ObservationService } from './observations.service';

@Module({
  imports: [TypeOrmModule.forFeature([Observation])],
  controllers: [ObservationsController],
  providers: [ObservationService],
})
export class ObservationsModule {}
