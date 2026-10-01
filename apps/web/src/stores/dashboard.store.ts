import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { api } from '@/services/api';
import { connectRealtime } from '@/services/realtime';
import type { Alert, Comfort, ComfortResponse, RealtimeObservation } from '@/types/domain';
import { useAlertsStore } from './alerts.store';
import { useObservationsStore } from './observations.store';

export const useDashboardStore = defineStore('dashboard', () => {
  const observations = useObservationsStore();
  const alerts = useAlertsStore();
  const comfort = ref<ComfortResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const realtimeConnected = ref(false);
  const realtimeError = ref<string | null>(null);
  const latest = computed(() => observations.latest);
  let disconnectRealtime: (() => void) | undefined;

  async function initialize(): Promise<void> {
    loading.value = true;
    error.value = null;
    await Promise.all([observations.fetchLatest(), observations.fetchHistory(), fetchComfort(), alerts.fetchAlerts()]);
    error.value = observations.error ?? alerts.error ?? error.value;
    loading.value = false;
    startRealtime();
  }

  async function fetchComfort(): Promise<void> {
    try {
      comfort.value = await api.getComfort();
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : 'Impossible de charger le confort.';
    }
  }

  function startRealtime(): void {
    if (disconnectRealtime) return;
    disconnectRealtime = connectRealtime({
      onConnectionChange: (connected) => {
        realtimeConnected.value = connected;
        if (connected) realtimeError.value = null;
      },
      onError: (message) => (realtimeError.value = message),
      onObservation: handleObservationCreated,
      onAlertCreated: handleAlertCreated,
      onAlertResolved: handleAlertResolved,
      onComfort: handleComfortUpdated,
    });
  }

  function stopRealtime(): void {
    disconnectRealtime?.();
    disconnectRealtime = undefined;
    realtimeConnected.value = false;
  }

  function handleObservationCreated(observation: RealtimeObservation): void {
    observations.handleCreated(observation);
  }

  function handleComfortUpdated(value: Comfort): void {
    comfort.value = value;
  }

  function handleAlertCreated(alert: Alert): void {
    alerts.handleCreated(alert);
  }

  function handleAlertResolved(alert: Alert): void {
    alerts.handleResolved(alert);
  }

  return {
    latest,
    comfort,
    loading,
    error,
    realtimeConnected,
    realtimeError,
    initialize,
    fetchComfort,
    startRealtime,
    stopRealtime,
    handleObservationCreated,
    handleComfortUpdated,
    handleAlertCreated,
    handleAlertResolved,
  };
});
