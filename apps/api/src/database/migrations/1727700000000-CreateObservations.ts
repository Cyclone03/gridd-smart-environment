import { MigrationInterface, QueryRunner } from 'typeorm';

export class CreateObservations1727700000000 implements MigrationInterface {
  name = 'CreateObservations1727700000000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query('CREATE EXTENSION IF NOT EXISTS "pgcrypto"');
    await queryRunner.query(
      `CREATE TYPE "observation_type_enum" AS ENUM ('temperature', 'humidity', 'co2', 'sound_level', 'occupancy')`,
    );
    await queryRunner.query(`
      CREATE TABLE "observations" (
        "id" uuid NOT NULL DEFAULT gen_random_uuid(),
        "node_id" character varying NOT NULL,
        "type" "observation_type_enum" NOT NULL,
        "value" double precision NOT NULL,
        "unit" character varying NOT NULL,
        "observed_at" TIMESTAMP WITH TIME ZONE,
        "received_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        "site_id" character varying,
        "site_label" character varying,
        "building_id" character varying,
        "building_label" character varying,
        "storey_id" character varying,
        "storey_label" character varying,
        "space_id" character varying,
        "space_label" character varying,
        "zone_id" character varying,
        "zone_label" character varying,
        "position_x" double precision,
        "position_y" double precision,
        "position_z" double precision,
        "metadata" jsonb,
        CONSTRAINT "PK_observations_id" PRIMARY KEY ("id")
      )
    `);
    await queryRunner.query(
      'CREATE INDEX "IDX_observations_type" ON "observations" ("type")',
    );
    await queryRunner.query(
      'CREATE INDEX "IDX_observations_node_id" ON "observations" ("node_id")',
    );
    await queryRunner.query(
      'CREATE INDEX "IDX_observations_observed_at" ON "observations" ("observed_at")',
    );
    await queryRunner.query(
      'CREATE INDEX "IDX_observations_space_id" ON "observations" ("space_id")',
    );
    await queryRunner.query(
      'CREATE INDEX "IDX_observations_zone_id" ON "observations" ("zone_id")',
    );
    await queryRunner.query(
      'CREATE INDEX "IDX_observations_building_id" ON "observations" ("building_id")',
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query('DROP INDEX "IDX_observations_building_id"');
    await queryRunner.query('DROP INDEX "IDX_observations_zone_id"');
    await queryRunner.query('DROP INDEX "IDX_observations_space_id"');
    await queryRunner.query('DROP INDEX "IDX_observations_observed_at"');
    await queryRunner.query('DROP INDEX "IDX_observations_node_id"');
    await queryRunner.query('DROP INDEX "IDX_observations_type"');
    await queryRunner.query('DROP TABLE "observations"');
    await queryRunner.query('DROP TYPE "observation_type_enum"');
  }
}
