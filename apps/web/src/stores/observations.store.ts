import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { api } from '@/services/api';
import type { Observation, ObservationType, RealtimeObservation } from '@/types/domain';

export const useObservationsStore = defineStore('observations', () => {
  const latest = ref<Observation[]>([]);
  const history = ref<Observation[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const latestByType = computed(
    () => new Map(latest.value.map((observation) => [observation.type, observation])),
  );

  async function fetchLatest(): Promise<void> {
    await load(async () => {
      latest.value = await api.getLatestObservations();
    });
  }

  async function fetchHistory(): Promise<void> {
    await load(async () => {
      history.value = await api.getObservations();
    });
  }

  function handleCreated(payload: RealtimeObservation): void {
    const observation: Observation = {
      id: payload.id,
      nodeId: payload.nodeId,
      type: payload.type,
      value: payload.value,
      unit: payload.unit,
      observedAt: payload.observedAt,
      receivedAt: payload.observedAt ?? new Date().toISOString(),
      siteId: null,
      siteLabel: null,
      buildingId: null,
      buildingLabel: null,
      storeyId: null,
      storeyLabel: null,
      spaceId: payload.space.id,
      spaceLabel: payload.space.label,
      zoneId: null,
      zoneLabel: null,
      metadata: null,
    };
    latest.value = [
      ...latest.value.filter((item) => item.type !== observation.type),
      observation,
    ];
    history.value = [observation, ...history.value.filter((item) => item.id !== observation.id)].slice(
      0,
      500,
    );
  }

  function byType(type: ObservationType): Observation | undefined {
    return latestByType.value.get(type);
  }

  async function load(action: () => Promise<void>): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await action();
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : 'Une erreur est survenue.';
    } finally {
      loading.value = false;
    }
  }

  return { latest, history, loading, error, latestByType, fetchLatest, fetchHistory, handleCreated, byType };
});
