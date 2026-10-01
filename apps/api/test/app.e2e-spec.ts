import { INestApplication } from '@nestjs/common';
import { Test, TestingModule } from '@nestjs/testing';
import request = require('supertest');
import { AppModule } from '../src/app.module';

describe('API endpoints (e2e)', () => {
  let app: INestApplication;

  beforeEach(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    app.setGlobalPrefix('api');
    await app.init();
  });

  afterEach(async () => {
    await app.close();
  });

  it('GET /api/health', () => {
    return request(app.getHttpServer())
      .get('/api/health')
      .expect(200)
      .expect({ status: 'ok', database: 'connected' });
  });

  it('GET /api/observations', () => {
    return request(app.getHttpServer())
      .get('/api/observations')
      .expect(200)
      .expect(({ body }) => {
        expect(Array.isArray(body)).toBe(true);
      });
  });

  it('GET /api/observations/latest', () => {
    return request(app.getHttpServer())
      .get('/api/observations/latest')
      .expect(200)
      .expect(({ body }) => {
        expect(Array.isArray(body)).toBe(true);
        const types = body.map(({ type }: { type: string }) => type);
        expect(new Set(types).size).toBe(types.length);
      });
  });

  it('GET /api/comfort', () => {
    return request(app.getHttpServer())
      .get('/api/comfort')
      .expect(200)
      .expect(({ body }) => {
        expect(['good', 'warning', 'critical', 'unavailable']).toContain(
          body.status,
        );
      });
  });

  it('GET /api/alerts', () => {
    return request(app.getHttpServer())
      .get('/api/alerts?status=all')
      .expect(200)
      .expect(({ body }) => {
        expect(Array.isArray(body)).toBe(true);
      });
  });
});
