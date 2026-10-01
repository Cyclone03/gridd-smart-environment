<script setup lang="ts">
import { ref } from 'vue';
import Message from 'primevue/message';
import Select from 'primevue/select';
import ProgressSpinner from 'primevue/progressspinner';
import ObservationChart from '@/components/charts/ObservationChart.vue';
import ComfortCard from '@/components/dashboard/ComfortCard.vue';
import MetricCard from '@/components/dashboard/MetricCard.vue';
import { useAlertsStore } from '@/stores/alerts.store';
import { useDashboardStore } from '@/stores/dashboard.store';
import { useObservationsStore } from '@/stores/observations.store';
import type { ObservationType } from '@/types/domain';

const dashboard = useDashboardStore();
const observations = useObservationsStore();
const alerts = useAlertsStore();
const metrics: ObservationType[] = ['temperature', 'humidity', 'co2', 'sound_level', 'occupancy'];
const chartTypes: ObservationType[] = ['temperature', 'humidity', 'co2', 'sound_level'];
const period = ref(1);
const periods = [
  { label: '15 minutes', value: 0.25 },
  { label: '1 heure', value: 1 },
  { label: '6 heures', value: 6 },
  { label: '24 heures', value: 24 },
];
</script>

<template>
  <section class="space-y-7">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div><p class="section-kicker">Vue d’ensemble</p><h2 class="mt-1 text-2xl font-semibold tracking-tight">Environnement du laboratoire</h2><p class="mt-1 text-sm text-slate-500">A-1540 · GRIDD · Pavillon A</p></div>
      <RouterLink to="/alerts" class="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium shadow-sm"><i class="pi pi-bell mr-2 text-brand-600" />{{ alerts.active.length }} alerte{{ alerts.active.length === 1 ? '' : 's' }} active{{ alerts.active.length === 1 ? '' : 's' }}</RouterLink>
    </div>

    <Message v-if="dashboard.error" severity="error" :closable="false">{{ dashboard.error }}</Message>
    <Message v-if="dashboard.realtimeError" severity="warn" :closable="false">{{ dashboard.realtimeError }}</Message>
    <div v-if="dashboard.loading && !observations.latest.length" class="grid min-h-48 place-items-center"><ProgressSpinner aria-label="Chargement du dashboard" /></div>

    <template v-else>
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard v-for="type in metrics" :key="type" :type="type" :observation="observations.byType(type)" />
      </div>

      <div class="grid gap-5 xl:grid-cols-[360px_1fr]">
        <ComfortCard :comfort="dashboard.comfort" />
        <div class="panel min-w-0 p-5">
          <div class="mb-4 flex flex-wrap items-center justify-between gap-3"><div><p class="section-kicker">Tendances</p><h2 class="section-title mt-1">Évolution des mesures</h2></div><Select v-model="period" :options="periods" option-label="label" option-value="value" class="w-40" aria-label="Période des graphiques" /></div>
          <div class="grid min-w-0 gap-6 md:grid-cols-2">
            <div v-for="type in chartTypes" :key="type" class="min-w-0 rounded-xl border border-slate-100 p-3"><h3 class="mb-2 text-sm font-semibold text-slate-700">{{ type === 'sound_level' ? 'Niveau sonore' : type === 'co2' ? 'CO₂' : type === 'temperature' ? 'Température' : 'Humidité' }}</h3><ObservationChart :observations="observations.history" :type="type" :period-hours="period" /></div>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>
