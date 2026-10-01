<script setup lang="ts">
import { computed } from 'vue';
import type { VisualStatus } from '@/utils/status';

const props = defineProps<{ status: VisualStatus }>();
const labels: Record<VisualStatus, string> = { normal: 'Normal', good: 'Bon', warning: 'Attention', critical: 'Critique', unavailable: 'Indisponible' };
const classes: Record<VisualStatus, string> = {
  normal: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  good: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-50 text-amber-800 border-amber-200',
  critical: 'bg-rose-50 text-rose-700 border-rose-200',
  unavailable: 'bg-slate-100 text-slate-600 border-slate-200',
};
const badgeClass = computed(() => classes[props.status]);
</script>

<template><span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold" :class="badgeClass">{{ labels[status] }}</span></template>
