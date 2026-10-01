import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { api } from '@/services/api';
import type { Observation, RealtimeObservation } from '@/types/domain';
import { useObservationsStore } from './observations.store';

vi.mock('@/services/api', () => ({
  api: { getLatestObservations: vi.fn(), getObservations: vi.fn() },
}));

describe('observations store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('loads latest observations', async () => {
    vi.mocked(api.getLatestObservations).mockResolvedValue([observation]);
    const store = useObservationsStore();
    await store.fetchLatest();
    expect(store.latest).toEqual([observation]);
    expect(store.error).toBeNull();
  });

  it('updates latest and history after observation.created', () => {
    const store = useObservationsStore();
    store.handleCreated(realtimeObservation);
    expect(store.byType('temperature')?.value).toBe(24.2);
    expect(store.history[0]?.id).toBe('realtime-1');
  });

  it('exposes a friendly API error', async () => {
    vi.mocked(api.getObservations).mockRejectedValue(new Error('Backend indisponible'));
    const store = useObservationsStore();
    await store.fetchHistory();
    expect(store.error).toBe('Backend indisponible');
    expect(store.loading).toBe(false);
  });
});

const observation = {
  id: 'observation-1', type: 'temperature', value: 23, unit: '°C', nodeId: 'node-1',
  observedAt: '2026-01-01T00:00:00.000Z', receivedAt: '2026-01-01T00:00:01.000Z',
  siteId: 'ets', siteLabel: 'ETS', buildingId: 'A', buildingLabel: 'Pavillon A',
  storeyId: '1', storeyLabel: '1er étage', spaceId: 'A-1540', spaceLabel: 'GRIDD',
  zoneId: 'office', zoneLabel: 'Bureau', metadata: null,
} satisfies Observation;

const realtimeObservation = {
  id: 'realtime-1', type: 'temperature', value: 24.2, unit: '°C', nodeId: 'node-1',
  observedAt: '2026-01-01T00:01:00.000Z', space: { id: 'A-1540', label: 'GRIDD' },
} satisfies RealtimeObservation;
