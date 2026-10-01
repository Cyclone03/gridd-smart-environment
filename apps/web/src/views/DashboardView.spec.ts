import { beforeEach, describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import DashboardView from './DashboardView.vue';
import { useDashboardStore } from '@/stores/dashboard.store';
import { useObservationsStore } from '@/stores/observations.store';
import type { Observation } from '@/types/domain';

describe('DashboardView', () => {
  let pinia: ReturnType<typeof createPinia>;
  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  it('renders environmental cards and the Comfort Index', () => {
    useObservationsStore().latest = [temperature];
    useDashboardStore().comfort = {
      spaceId: 'A-1540', score: 87, status: 'good',
      components: { temperature: 95, humidity: 90, co2: 85, noise: 78 },
    };
    const wrapper = render();
    expect(wrapper.text()).toContain('Température');
    expect(wrapper.text()).toContain('Humidité');
    expect(wrapper.text()).toContain('CO₂');
    expect(wrapper.text()).toContain('Niveau sonore');
    expect(wrapper.text()).toContain('Occupation');
    expect(wrapper.text()).toContain('87');
  });

  it('shows explicit empty states when observations are unavailable', () => {
    const wrapper = render();
    expect(wrapper.text()).toContain('Aucune donnée');
    expect(wrapper.text()).toContain('Indisponible');
  });

  function render() {
    return mount(DashboardView, {
      global: {
        plugins: [pinia],
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
          ObservationChart: { template: '<div data-test="chart" />' },
          Select: { template: '<div />' },
          Message: { template: '<div><slot /></div>' },
          ProgressSpinner: { template: '<div />' },
        },
      },
    });
  }
});

const temperature = {
  id: 'temperature-1', nodeId: 'temp-node', type: 'temperature', value: 23.4, unit: '°C',
  observedAt: '2026-01-01T00:00:00.000Z', receivedAt: '2026-01-01T00:00:01.000Z',
  siteId: 'ets', siteLabel: 'ETS', buildingId: 'A', buildingLabel: 'Pavillon A',
  storeyId: '1', storeyLabel: '1er étage', spaceId: 'A-1540', spaceLabel: 'GRIDD',
  zoneId: 'office', zoneLabel: 'Bureau', metadata: null,
} satisfies Observation;
