<script setup lang="ts">
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import Message from 'primevue/message';
import Tag from 'primevue/tag';
import { useAlertsStore } from '@/stores/alerts.store';

const store = useAlertsStore();
const formatDate = (value: string | null) => value ? new Intl.DateTimeFormat('fr-CA', { dateStyle: 'short', timeStyle: 'medium' }).format(new Date(value)) : '—';
const label = (type: string) => ({ HIGH_CO2: 'CO₂ élevé', HIGH_SOUND_LEVEL: 'Niveau sonore élevé', HIGH_TEMPERATURE: 'Température élevée' }[type] ?? type);
</script>

<template>
  <section class="space-y-6">
    <div><p class="section-kicker">Surveillance</p><h2 class="mt-1 text-2xl font-semibold">Alertes environnementales</h2><p class="mt-1 text-sm text-slate-500">Les alertes critiques sont créées uniquement au franchissement des seuils configurés.</p></div>
    <Message v-if="store.error" severity="error" :closable="false">{{ store.error }}</Message>

    <div class="panel overflow-hidden">
      <div class="border-b border-slate-100 p-5"><h3 class="section-title">Alertes actives <span class="ml-2 rounded-full bg-rose-50 px-2 py-1 text-xs text-rose-700">{{ store.active.length }}</span></h3></div>
      <div class="space-y-3 p-4 md:hidden">
        <article v-for="alert in store.active" :key="alert.id" class="rounded-xl border border-rose-100 bg-rose-50/40 p-4">
          <div class="flex items-center justify-between gap-2"><b>{{ label(alert.type) }}</b><Tag :value="alert.severity === 'critical' ? 'Critique' : 'Attention'" :severity="alert.severity === 'critical' ? 'danger' : 'warn'" /></div>
          <p class="mt-2 text-sm">{{ alert.value }} {{ alert.unit }} · seuil {{ alert.threshold }} {{ alert.unit }}</p>
          <p class="mt-1 text-xs text-slate-500">{{ alert.zoneId || 'Zone inconnu' }} · {{ formatDate(alert.createdAt) }}</p>
        </article>
        <p v-if="!store.active.length" class="py-6 text-center text-sm text-slate-500">Aucune alerte active</p>
      </div>
      <DataTable :value="store.active" :loading="store.loading" scrollable table-style="min-width: 850px">
        <template #empty><div class="py-10 text-center"><i class="pi pi-check-circle mb-3 text-3xl text-emerald-500" /><p class="font-medium">Aucune alerte active</p><p class="text-sm text-slate-500">Tous les paramètres critiques sont sous contrôle.</p></div></template>
        <Column header="Alerte"><template #body="{ data }"><span class="font-semibold">{{ label(data.type) }}</span></template></Column>
        <Column header="Sévérité"><template #body="{ data }"><Tag :value="data.severity === 'critical' ? 'Critique' : 'Attention'" :severity="data.severity === 'critical' ? 'danger' : 'warn'" /></template></Column>
        <Column header="Mesure"><template #body="{ data }">{{ data.value }} {{ data.unit }}</template></Column>
        <Column header="Seuil"><template #body="{ data }">{{ data.threshold }} {{ data.unit }}</template></Column>
        <Column field="zoneId" header="Zone" />
        <Column header="Créée"><template #body="{ data }">{{ formatDate(data.createdAt) }}</template></Column>
      </DataTable>
    </div>

    <div class="panel overflow-hidden">
      <div class="border-b border-slate-100 p-5"><h3 class="section-title">Historique</h3></div>
      <DataTable :value="store.history" :loading="store.loading" paginator :rows="10" scrollable table-style="min-width: 900px">
        <template #empty><div class="py-8 text-center text-slate-500">Aucune alerte résolue.</div></template>
        <Column header="Alerte"><template #body="{ data }">{{ label(data.type) }}</template></Column>
        <Column field="severity" header="Sévérité" />
        <Column header="Valeur"><template #body="{ data }">{{ data.value }} {{ data.unit }}</template></Column>
        <Column field="zoneId" header="Zone" />
        <Column header="Créée"><template #body="{ data }">{{ formatDate(data.createdAt) }}</template></Column>
        <Column header="Résolue"><template #body="{ data }">{{ formatDate(data.resolvedAt) }}</template></Column>
      </DataTable>
    </div>
  </section>
</template>
