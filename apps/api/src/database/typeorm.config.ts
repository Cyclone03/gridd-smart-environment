import { ConfigService } from '@nestjs/config';
import { TypeOrmModuleOptions } from '@nestjs/typeorm';
import { Observation } from '../observations/entities/observation.entity';

export function createTypeOrmOptions(
  configService: ConfigService,
): TypeOrmModuleOptions {
  return {
    type: 'postgres',
    host: configService.get<string>('DATABASE_HOST', 'localhost'),
    port: configService.get<number>('DATABASE_PORT', 5432),
    database: configService.get<string>('DATABASE_NAME', 'gridd_dashboard'),
    username: configService.get<string>('DATABASE_USER', 'gridd'),
    password: configService.get<string>('DATABASE_PASSWORD', ''),
    entities: [Observation],
    migrations: [__dirname + '/migrations/*{.ts,.js}'],
    synchronize: false,
  };
}
