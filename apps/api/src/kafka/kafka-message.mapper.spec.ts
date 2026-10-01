import { ObservationType } from '../observations/entities/observation.entity';
import {
  InvalidKafkaObservationError,
  mapKafkaObservation,
} from './kafka-message.mapper';

const cases = [
  ['gridd.obs.environmental.temperature', 'temperature', '°C'],
  ['gridd.obs.environmental.humidity', 'humidity', '%'],
  ['gridd.obs.environmental.co2', 'co2', 'ppm'],
  ['gridd.obs.acoustic.sound_level', 'sound_level', 'dBA'],
  ['gridd.obs.occupancy.count', 'occupancy', 'person'],
] as const;

describe('Kafka observation mapping', () => {
  it.each(cases)('maps %s to an ObservationInput', (topic, type, unit) => {
    const result = mapKafkaObservation(
      topic,
      message({ node_id: `node-${type}`, type, value: 42, unit }),
    );

    expect(result).toMatchObject({
      nodeId: `node-${type}`,
      type: type as ObservationType,
      value: 42,
      unit,
      observedAt: null,
    });
  });

  it('maps the timestamp and complete GRIDD location metadata', () => {
    const metadata = {
      site: { id: 'ets', label: 'ÉTS' },
      building: { id: 'A', label: 'Pavillon A' },
      storey: { id: '1', label: '1er étage' },
      space: { id: 'A-1540', label: 'GRIDD', type: 'laboratory' },
      zone: { id: 'professors-office', label: 'Bureau des professeurs' },
      position: {
        x: 1.2,
        y: 2.3,
        z: 1.5,
        unit: 'm',
        coordinateSystem: 'A-1540-local',
      },
    };
    const result = mapKafkaObservation(
      cases[0][0],
      message({
        node_id: 'node-1',
        type: 'temperature',
        value: 23.5,
        unit: '°C',
        timestamp: '2026-10-01T14:30:00.000Z',
        metadata,
      }),
    );

    expect(result).toMatchObject({
      observedAt: new Date('2026-10-01T14:30:00.000Z'),
      siteId: 'ets',
      buildingId: 'A',
      storeyId: '1',
      spaceId: 'A-1540',
      zoneId: 'professors-office',
      positionX: 1.2,
      positionY: 2.3,
      positionZ: 1.5,
      metadata,
    });
  });

  it.each([
    ['invalid JSON', Buffer.from('{')],
    ['missing node_id', message({ type: 'temperature', value: 20, unit: '°C' })],
    ['inconsistent type', message({ node_id: 'n1', type: 'humidity', value: 20, unit: '%' })],
    ['missing unit', message({ node_id: 'n1', type: 'temperature', value: 20 })],
    ['non-finite value', message({ node_id: 'n1', type: 'temperature', value: '20', unit: '°C' })],
    ['invalid metadata', message({ node_id: 'n1', type: 'temperature', value: 20, unit: '°C', metadata: 'invalid' })],
  ])('rejects %s', (_description, value) => {
    expect(() => mapKafkaObservation(cases[0][0], value)).toThrow(
      InvalidKafkaObservationError,
    );
  });
});

function message(payload: Record<string, unknown>): Buffer {
  return Buffer.from(JSON.stringify(payload));
}
