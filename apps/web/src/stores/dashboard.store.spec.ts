import { beforeEach, describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useObservationsStore } from './observations.store';
import { useDashboardStore } from './dashboard.store';

describe('dashboard store realtime updates', () => {
  beforeEach(() => setActivePinia(createPinia()));

  it('updates observations after observation.created', () => {
    const dashboard = useDashboardStore();
    dashboard.handleObservationCreated({
      id: 'observation-live', nodeId: 'temp-node', type: 'temperature', value: 25.1,
      unit: '°C', observedAt: '2026-01-01T00:00:00.000Z',
      space: { id: 'A-1540', label: 'GRIDD' },
    });
    expect(useObservationsStore().byType('temperature')?.value).toBe(25.1);
  });

  it('updates the Comfort Index after comfort.updated', () => {
    const dashboard = useDashboardStore();
    dashboard.handleComfortUpdated({
      spaceId: 'A-1540', score: 87, status: 'good',
      components: { temperature: 95, humidity: 90, co2: 85, noise: 78 },
    });
    expect(dashboard.comfort).toMatchObject({ score: 87, status: 'good' });
  });
});
