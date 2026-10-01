import { Module } from '@nestjs/common';
import { ObservationsModule } from '../observations/observations.module';
import { SimulatorService } from './simulator.service';

@Module({
  imports: [ObservationsModule],
  providers: [SimulatorService],
})
export class SimulatorModule {}
