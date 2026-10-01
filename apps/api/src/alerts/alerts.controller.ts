import { BadRequestException, Controller, Get, Query } from '@nestjs/common';
import { Alert } from './entities/alert.entity';
import { AlertFilter, AlertsService } from './alerts.service';

@Controller('alerts')
export class AlertsController {
  constructor(private readonly alertsService: AlertsService) {}

  @Get()
  find(@Query('status') status: string = 'active'): Promise<Alert[]> {
    if (!['active', 'history', 'all'].includes(status)) {
      throw new BadRequestException(
        'status must be one of: active, history, all',
      );
    }
    return this.alertsService.find(status as AlertFilter);
  }
}
