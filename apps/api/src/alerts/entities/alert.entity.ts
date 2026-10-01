import {
  Column,
  CreateDateColumn,
  Entity,
  Index,
  PrimaryGeneratedColumn,
} from 'typeorm';

export enum AlertType {
  HIGH_CO2 = 'HIGH_CO2',
  HIGH_SOUND_LEVEL = 'HIGH_SOUND_LEVEL',
  HIGH_TEMPERATURE = 'HIGH_TEMPERATURE',
}

export enum AlertSeverity {
  WARNING = 'warning',
  CRITICAL = 'critical',
}

@Entity({ name: 'alerts' })
@Index('IDX_alerts_type', ['type'])
@Index('IDX_alerts_created_at', ['createdAt'])
@Index('IDX_alerts_resolved_at', ['resolvedAt'])
@Index('UQ_alerts_active_context', ['type', 'nodeId', 'spaceId'], {
  unique: true,
  where: '"resolved_at" IS NULL',
})
export class Alert {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ type: 'enum', enum: AlertType, enumName: 'alert_type_enum' })
  type!: AlertType;

  @Column({
    type: 'enum',
    enum: AlertSeverity,
    enumName: 'alert_severity_enum',
  })
  severity!: AlertSeverity;

  @Column({ type: 'double precision' })
  value!: number;

  @Column({ type: 'double precision' })
  threshold!: number;

  @Column({ type: 'varchar' })
  unit!: string;

  @Column({ name: 'node_id', type: 'varchar' })
  nodeId!: string;

  @Column({ name: 'space_id', type: 'varchar', nullable: true })
  spaceId!: string | null;

  @CreateDateColumn({ name: 'created_at', type: 'timestamptz' })
  createdAt!: Date;

  @Column({ name: 'resolved_at', type: 'timestamptz', nullable: true })
  resolvedAt!: Date | null;
}
