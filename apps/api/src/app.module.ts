import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { createTypeOrmOptions } from './database/typeorm.config';
import { HealthController } from './health/health.controller';
import { HealthService } from './health/health.service';
import { ObservationsModule } from './observations/observations.module';
import { SimulatorModule } from './simulator/simulator.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env', '../../.env'],
    }),
    TypeOrmModule.forRootAsync({
      inject: [ConfigService],
      useFactory: createTypeOrmOptions,
    }),
    ObservationsModule,
    SimulatorModule,
  ],
  controllers: [HealthController],
  providers: [HealthService],
})
export class AppModule {}
