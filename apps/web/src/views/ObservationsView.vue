<script setup lang="ts">
import { computed, ref } from 'vue';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import Message from 'primevue/message';
import Select from 'primevue/select';
import { useObservationsStore } from '@/stores/observations.store';

const store = useObservationsStore();
const type = ref<string | null>(null);
const spaceId = ref<string | null>(null);
const period = ref(24);
const typeOptions = [
  { label: 'Tous les types', value: null },
  { label: 'Température', value: 'temperature' },
  { label: 'Humidité', value: 'humidity' },
  { label: 'CO₂', value: 'co2' },
  { label: 'Niveau sonore', value: 'sound_level' },
  { label: 'Occupation', value: 'occupancy' },
];
const periodOptions = [
  { label: '15 minutes', value: 0.25 }, { label: '1 heure', value: 1 },
  { label: '6 heures', value: 6 }, { label: '24 heures', value: 24 },
];
const spaceOptions = computed(() => [
  { label: 'Tous les espaces', value: null },
  ...[...new Set(store.history.map((item) => item.spaceId).filter(Boolean))].map((value) => ({ label: value!, value })),
]);
const filtered = computed(() => {
  const cutoff = Date.now() - period.value * 60 * 60 * 1000;
  return store.history.filter((item) =>
    (!type.value || item.type === type.value) &&
    (!spaceId.value || item.spaceId === spaceId.value) &&
    new Date(item.observedAt ?? item.receivedAt).getTime() >= cutoff,
  );
});
const formatDate = (value: string | null) => value ? new Intl.DateTimeFormat('fr-CA', { dateStyle: 'short', timeStyle: 'medium' }).format(new Date(value)) : '—';
</script>

<template>
  <section class="space-y-5">
    <div><p class="section-kicker">Données brutes</p><h2 class="mt-1 text-2xl font-semibold">Historique des observations</h2><p class="mt-1 text-sm text-slate-500">Explorez les mesures reçues et persistées par le backend.</p></div>
    <Message v-if="store.error" severity="error" :closable="false">{{ store.error }}</Message>
    <div class="panel p-4">
      <div class="mb-4 grid gap-3 sm:grid-cols-3">
        <Select v-model="type" :options="typeOptions" option-label="label" option-value="value" placeholder="Type" fluid />
        <Select v-model="spaceId" :options="spaceOptions" option-label="label" option-value="value" placeholder="Espace" fluid />
        <Select v-model="period" :options="periodOptions" option-label="label" option-value="value" placeholder="Période" fluid />
      </div>
      <DataTable :value="filtered" :loading="store.loading" paginator :rows="15" striped-rows scrollable table-style="min-width: 900px">
        <template #empty><div class="py-8 text-center text-slate-500">Aucune observation pour ces filtres.</div></template>
        <Column field="type" header="Type" sortable />
        <Column header="Valeur"><template #body="{ data }"><b>{{ data.value }}</b> {{ data.unit }}</template></Column>
        <Column field="nodeId" header="Nœud" />
        <Column field="spaceId" header="Espace"><template #body="{ data }">{{ data.spaceLabel || data.spaceId || '—' }}</template></Column>
        <Column field="zoneId" header="Zone"><template #body="{ data }">{{ data.zoneLabel || data.zoneId || '—' }}</template></Column>
        <Column header="Horodatage" sortable><template #body="{ data }">{{ formatDate(data.observedAt || data.receivedAt) }}</template></Column>
      </DataTable>
    </div>
  </section>
</template>
