import { ref } from 'vue';
import { defineStore } from 'pinia';
import { api } from '@/services/api';
import type { Alert } from '@/types/domain';

export const useAlertsStore = defineStore('alerts', () => {
  const active = ref<Alert[]>([]);
  const history = ref<Alert[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchAlerts(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      [active.value, history.value] = await Promise.all([
        api.getAlerts('active'),
        api.getAlerts('history'),
      ]);
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : 'Impossible de charger les alertes.';
    } finally {
      loading.value = false;
    }
  }

  function handleCreated(alert: Alert): void {
    active.value = [alert, ...active.value.filter((item) => item.id !== alert.id)];
  }

  function handleResolved(alert: Alert): void {
    active.value = active.value.filter((item) => item.id !== alert.id);
    history.value = [alert, ...history.value.filter((item) => item.id !== alert.id)];
  }

  return { active, history, loading, error, fetchAlerts, handleCreated, handleResolved };
});
