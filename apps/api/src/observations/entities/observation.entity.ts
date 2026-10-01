import {
  Column,
  CreateDateColumn,
  Entity,
  Index,
  PrimaryGeneratedColumn,
} from 'typeorm';

export enum ObservationType {
  TEMPERATURE = 'temperature',
  HUMIDITY = 'humidity',
  CO2 = 'co2',
  SOUND_LEVEL = 'sound_level',
  OCCUPANCY = 'occupancy',
}

@Entity({ name: 'observations' })
@Index('IDX_observations_type', ['type'])
@Index('IDX_observations_node_id', ['nodeId'])
@Index('IDX_observations_observed_at', ['observedAt'])
@Index('IDX_observations_space_id', ['spaceId'])
@Index('IDX_observations_zone_id', ['zoneId'])
@Index('IDX_observations_building_id', ['buildingId'])
export class Observation {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'node_id', type: 'varchar' })
  nodeId!: string;

  @Column({ type: 'enum', enum: ObservationType, enumName: 'observation_type_enum' })
  type!: ObservationType;

  @Column({ type: 'double precision' })
  value!: number;

  @Column({ type: 'varchar' })
  unit!: string;

  @Column({ name: 'observed_at', type: 'timestamptz', nullable: true })
  observedAt!: Date | null;

  @CreateDateColumn({ name: 'received_at', type: 'timestamptz' })
  receivedAt!: Date;

  @Column({ name: 'site_id', type: 'varchar', nullable: true })
  siteId!: string | null;

  @Column({ name: 'site_label', type: 'varchar', nullable: true })
  siteLabel!: string | null;

  @Column({ name: 'building_id', type: 'varchar', nullable: true })
  buildingId!: string | null;

  @Column({ name: 'building_label', type: 'varchar', nullable: true })
  buildingLabel!: string | null;

  @Column({ name: 'storey_id', type: 'varchar', nullable: true })
  storeyId!: string | null;

  @Column({ name: 'storey_label', type: 'varchar', nullable: true })
  storeyLabel!: string | null;

  @Column({ name: 'space_id', type: 'varchar', nullable: true })
  spaceId!: string | null;

  @Column({ name: 'space_label', type: 'varchar', nullable: true })
  spaceLabel!: string | null;

  @Column({ name: 'zone_id', type: 'varchar', nullable: true })
  zoneId!: string | null;

  @Column({ name: 'zone_label', type: 'varchar', nullable: true })
  zoneLabel!: string | null;

  @Column({ name: 'position_x', type: 'double precision', nullable: true })
  positionX!: number | null;

  @Column({ name: 'position_y', type: 'double precision', nullable: true })
  positionY!: number | null;

  @Column({ name: 'position_z', type: 'double precision', nullable: true })
  positionZ!: number | null;

  @Column({ type: 'jsonb', nullable: true })
  metadata!: Record<string, unknown> | null;
}
