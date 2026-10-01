import { Server } from 'socket.io';
import { Alert, AlertType } from '../alerts/entities/alert.entity';
import {
  Observation,
  ObservationType,
} from '../observations/entities/observation.entity';
import { RealtimeGateway } from './realtime.gateway';

describe('RealtimeGateway', () => {
  let gateway: RealtimeGateway;
  const server = { emit: jest.fn() } as unknown as Server;

  beforeEach(() => {
    jest.clearAllMocks();
    gateway = new RealtimeGateway();
    gateway.server = server;
  });

  it('emits observation.created with the public payload', () => {
    gateway.emitObservationCreated({
      id: 'observation-id',
      type: ObservationType.TEMPERATURE,
      value: 23.4,
      unit: '°C',
      nodeId: 'node-1',
      spaceId: 'A-1540',
      spaceLabel: 'GRIDD',
      observedAt: new Date('2026-01-01T00:00:00.000Z'),
    } as Observation);

    expect(server.emit).toHaveBeenCalledWith('observation.created', {
      id: 'observation-id',
      type: 'temperature',
      value: 23.4,
      unit: '°C',
      nodeId: 'node-1',
      space: { id: 'A-1540', label: 'GRIDD' },
      observedAt: '2026-01-01T00:00:00.000Z',
    });
  });

  it('emits alert lifecycle and comfort events', () => {
    const alert = { id: 'alert-id', type: AlertType.HIGH_CO2 } as Alert;
    const comfort = {
      spaceId: 'A-1540',
      score: 90,
      status: 'good' as const,
      components: { temperature: 100, humidity: 90, co2: 80, noise: 90 },
    };

    gateway.emitAlertCreated(alert);
    gateway.emitAlertResolved(alert);
    gateway.emitComfortUpdated(comfort);

    expect(server.emit).toHaveBeenCalledWith('alert.created', alert);
    expect(server.emit).toHaveBeenCalledWith('alert.resolved', alert);
    expect(server.emit).toHaveBeenCalledWith('comfort.updated', comfort);
  });
});
