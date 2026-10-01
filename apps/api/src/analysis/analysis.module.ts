import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Observation } from '../observations/entities/observation.entity';
import { AnalysisController } from './analysis.controller';
import { AnalysisService } from './analysis.service';
import environmentConfig from './environment.config';

@Module({
  imports: [
    ConfigModule.forFeature(environmentConfig),
    TypeOrmModule.forFeature([Observation]),
  ],
  controllers: [AnalysisController],
  providers: [AnalysisService],
  exports: [AnalysisService],
})
export class AnalysisModule {}
