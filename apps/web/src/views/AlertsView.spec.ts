import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import AlertsView from './AlertsView.vue';
import { useAlertsStore } from '@/stores/alerts.store';
import type { Alert } from '@/types/domain';

describe('AlertsView', () => {
  it('displays an active alert with its threshold', () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    useAlertsStore().active = [activeAlert];
    const wrapper = mount(AlertsView, {
      global: {
        plugins: [pinia],
        stubs: {
          DataTable: { template: '<div />' },
          Column: { template: '<span />' },
          Message: { template: '<div><slot /></div>' },
          Tag: { props: ['value'], template: '<span>{{ value }}</span>' },
        },
      },
    });
    expect(wrapper.text()).toContain('CO₂ élevé');
    expect(wrapper.text()).toContain('1301 ppm');
    expect(wrapper.text()).toContain('seuil 1200 ppm');
    expect(wrapper.text()).toContain('Critique');
  });
});

const activeAlert = {
  id: 'alert-1', type: 'HIGH_CO2', severity: 'critical', value: 1301, threshold: 1200,
  unit: 'ppm', nodeId: 'co2-node', spaceId: 'A-1540',
  createdAt: '2026-01-01T00:00:00.000Z', resolvedAt: null,
} satisfies Alert;
