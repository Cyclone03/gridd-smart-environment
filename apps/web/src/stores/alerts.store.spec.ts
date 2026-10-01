import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { api } from '@/services/api';
import type { Alert } from '@/types/domain';
import { useAlertsStore } from './alerts.store';

vi.mock('@/services/api', () => ({ api: { getAlerts: vi.fn() } }));

describe('alerts store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('loads active alerts and history', async () => {
    vi.mocked(api.getAlerts)
      .mockResolvedValueOnce([activeAlert])
      .mockResolvedValueOnce([]);
    const store = useAlertsStore();
    await store.fetchAlerts();
    expect(store.active).toEqual([activeAlert]);
    expect(api.getAlerts).toHaveBeenCalledWith('history');
  });

  it('moves an alert to history after alert.resolved', () => {
    const store = useAlertsStore();
    store.handleCreated(activeAlert);
    const resolved = { ...activeAlert, resolvedAt: '2026-01-01T00:10:00.000Z' };
    store.handleResolved(resolved);
    expect(store.active).toHaveLength(0);
    expect(store.history[0]).toEqual(resolved);
  });
});

export const activeAlert = {
  id: 'alert-1', type: 'HIGH_CO2', severity: 'critical', value: 1301, threshold: 1200,
  unit: 'ppm', nodeId: 'co2-node', spaceId: 'A-1540',
  createdAt: '2026-01-01T00:00:00.000Z', resolvedAt: null,
} satisfies Alert;
