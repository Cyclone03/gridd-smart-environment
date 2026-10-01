<script setup lang="ts">
import { computed } from 'vue';
import StatusBadge from '@/components/common/StatusBadge.vue';
import type { Observation, ObservationType } from '@/types/domain';
import { metricLabels, observationStatus } from '@/utils/status';

const props = defineProps<{ type: ObservationType; observation?: Observation }>();
const metric = computed(() => metricLabels[props.type]);
const status = computed(() => observationStatus(props.observation));
const updatedAt = computed(() => {
  const value = props.observation?.observedAt ?? props.observation?.receivedAt;
  return value ? new Intl.DateTimeFormat('fr-CA', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value)) : 'Aucune donnée';
});
</script>

<template>
  <article class="panel relative overflow-hidden p-5">
    <div class="absolute right-0 top-0 h-20 w-20 rounded-bl-full bg-brand-50" />
    <div class="relative flex items-start justify-between gap-3">
      <div class="grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-brand-700"><i :class="metric.icon" /></div>
      <StatusBadge :status="status" />
    </div>
    <p class="mt-5 text-sm font-medium text-slate-500">{{ metric.label }}</p>
    <div class="mt-1 flex items-baseline gap-2">
      <strong class="text-3xl font-semibold tracking-tight text-slate-900">{{ observation?.value ?? '—' }}</strong>
      <span class="text-sm font-medium text-slate-500">{{ observation?.unit ?? '' }}</span>
    </div>
    <p class="mt-4 text-xs text-slate-400">Mise à jour · {{ updatedAt }}</p>
  </article>
</template>
