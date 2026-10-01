<script setup lang="ts">
import { computed } from 'vue';
import StatusBadge from '@/components/common/StatusBadge.vue';
import type { ComfortResponse } from '@/types/domain';

const props = defineProps<{ comfort: ComfortResponse | null }>();
const available = computed(() => props.comfort && props.comfort.status !== 'unavailable' ? props.comfort : null);
const components = computed(() => available.value ? Object.entries(available.value.components) : []);
const labels: Record<string, string> = { temperature: 'Température', humidity: 'Humidité', co2: 'CO₂', noise: 'Bruit' };
</script>

<template>
  <article class="panel p-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div><p class="section-kicker">Indice synthétique</p><h2 class="section-title mt-1">Comfort Index</h2></div>
      <StatusBadge :status="available?.status ?? 'unavailable'" />
    </div>
    <template v-if="available">
      <div class="my-6 flex items-end gap-2"><strong class="text-6xl font-semibold tracking-[-0.06em] text-brand-700">{{ available.score }}</strong><span class="mb-2 text-lg text-slate-400">/100</span></div>
      <div class="grid grid-cols-2 gap-3">
        <div v-for="[key, value] in components" :key="key" class="rounded-xl bg-slate-50 p-3">
          <div class="flex justify-between text-xs"><span class="text-slate-500">{{ labels[key] }}</span><b>{{ value }}</b></div>
          <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200"><div class="h-full rounded-full bg-brand-500" :style="{ width: `${value}%` }" /></div>
        </div>
      </div>
    </template>
    <div v-else class="mt-6 rounded-xl border border-dashed border-slate-300 p-5 text-sm text-slate-500">Les quatre mesures nécessaires ne sont pas encore disponibles.</div>
  </article>
</template>
