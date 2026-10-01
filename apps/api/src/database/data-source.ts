import 'reflect-metadata';
import { config } from 'dotenv';
import { resolve } from 'node:path';
import { DataSource } from 'typeorm';
import { Observation } from '../observations/entities/observation.entity';

config({ path: resolve(__dirname, '../../../../.env') });

export default new DataSource({
  type: 'postgres',
  host: process.env.DATABASE_HOST ?? 'localhost',
  port: Number(process.env.DATABASE_PORT ?? 5432),
  database: process.env.DATABASE_NAME ?? 'gridd_dashboard',
  username: process.env.DATABASE_USER ?? 'gridd',
  password: process.env.DATABASE_PASSWORD ?? '',
  entities: [Observation],
  migrations: [resolve(__dirname, 'migrations/*{.ts,.js}')],
  synchronize: false,
});
