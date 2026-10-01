import { NestFactory } from '@nestjs/core';
import { ConfigService } from '@nestjs/config';
import { AppModule } from './app.module';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule);
  const configService = app.get(ConfigService);

  app.setGlobalPrefix('api');
  app.enableCors({
    origin: configService.get<string>('WEB_ORIGIN', 'http://localhost:5173'),
    credentials: true,
  });

  const port = configService.get<number>('PORT', 3000);
  await app.listen(port);
}

void bootstrap();
