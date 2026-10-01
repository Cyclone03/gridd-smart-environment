import { MigrationInterface, QueryRunner } from 'typeorm';

export class CreateAlerts1727800000000 implements MigrationInterface {
  name = 'CreateAlerts1727800000000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `CREATE TYPE "alert_type_enum" AS ENUM ('HIGH_CO2', 'HIGH_SOUND_LEVEL', 'HIGH_TEMPERATURE')`,
    );
    await queryRunner.query(
      `CREATE TYPE "alert_severity_enum" AS ENUM ('warning', 'critical')`,
    );
    await queryRunner.query(`
      CREATE TABLE "alerts" (
        "id" uuid NOT NULL DEFAULT gen_random_uuid(),
        "type" "alert_type_enum" NOT NULL,
        "severity" "alert_severity_enum" NOT NULL,
        "value" double precision NOT NULL,
        "threshold" double precision NOT NULL,
        "unit" character varying NOT NULL,
        "node_id" character varying NOT NULL,
        "space_id" character varying,
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        "resolved_at" TIMESTAMP WITH TIME ZONE,
        CONSTRAINT "PK_alerts_id" PRIMARY KEY ("id")
      )
    `);
    await queryRunner.query(
      'CREATE INDEX "IDX_alerts_type" ON "alerts" ("type")',
    );
    await queryRunner.query(
      'CREATE INDEX "IDX_alerts_created_at" ON "alerts" ("created_at")',
    );
    await queryRunner.query(
      'CREATE INDEX "IDX_alerts_resolved_at" ON "alerts" ("resolved_at")',
    );
    await queryRunner.query(`
      CREATE UNIQUE INDEX "UQ_alerts_active_context"
      ON "alerts" ("type", "node_id", "space_id")
      WHERE "resolved_at" IS NULL
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query('DROP INDEX "UQ_alerts_active_context"');
    await queryRunner.query('DROP INDEX "IDX_alerts_resolved_at"');
    await queryRunner.query('DROP INDEX "IDX_alerts_created_at"');
    await queryRunner.query('DROP INDEX "IDX_alerts_type"');
    await queryRunner.query('DROP TABLE "alerts"');
    await queryRunner.query('DROP TYPE "alert_severity_enum"');
    await queryRunner.query('DROP TYPE "alert_type_enum"');
  }
}
