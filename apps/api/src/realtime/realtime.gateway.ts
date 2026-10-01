import {
  WebSocketGateway,
  WebSocketServer,
} from '@nestjs/websockets';
import { Server } from 'socket.io';
import { ComfortResult } from '../analysis/comfort.types';
import { Alert } from '../alerts/entities/alert.entity';
import { Observation } from '../observations/entities/observation.entity';

@WebSocketGateway({
  namespace: '/realtime',
  cors: {
    origin: process.env.WEB_ORIGIN ?? 'http://localhost:5173',
    credentials: true,
  },
})
export class RealtimeGateway {
  @WebSocketServer()
  server!: Server;

  emitObservationCreated(observation: Observation): void {
    this.server.emit('observation.created', {
      id: observation.id,
      type: observation.type,
      value: observation.value,
      unit: observation.unit,
      nodeId: observation.nodeId,
      space: {
        id: observation.spaceId,
        label: observation.spaceLabel,
      },
      observedAt: observation.observedAt?.toISOString() ?? null,
    });
  }

  emitAlertCreated(alert: Alert): void {
    this.server.emit('alert.created', alert);
  }

  emitAlertResolved(alert: Alert): void {
    this.server.emit('alert.resolved', alert);
  }

  emitComfortUpdated(comfort: ComfortResult): void {
    this.server.emit('comfort.updated', comfort);
  }
}
