import { ObservationType } from '../entities/observation.entity';

export interface ObservationInput {
  nodeId: string;
  type: ObservationType;
  value: number;
  unit: string;
  observedAt: Date | null;
  siteId: string | null;
  siteLabel: string | null;
  buildingId: string | null;
  buildingLabel: string | null;
  storeyId: string | null;
  storeyLabel: string | null;
  spaceId: string | null;
  spaceLabel: string | null;
  zoneId: string | null;
  zoneLabel: string | null;
  positionX: number | null;
  positionY: number | null;
  positionZ: number | null;
  metadata: Record<string, unknown> | null;
}
