<script setup lang="ts">
import { computed } from 'vue';
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js';
import { Line } from 'vue-chartjs';
import type { Observation, ObservationType } from '@/types/domain';
import { metricLabels } from '@/utils/status';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const props = defineProps<{ observations: Observation[]; type: ObservationType; periodHours: number }>();
const points = computed(() => {
  const cutoff = Date.now() - props.periodHours * 60 * 60 * 1000;
  return props.observations
    .filter((item) => item.type === props.type && new Date(item.observedAt ?? item.receivedAt).getTime() >= cutoff)
    .sort((a, b) => new Date(a.observedAt ?? a.receivedAt).getTime() - new Date(b.observedAt ?? b.receivedAt).getTime());
});
const chartData = computed(() => ({
  labels: points.value.map((item) => new Intl.DateTimeFormat('fr-CA', { hour: '2-digit', minute: '2-digit' }).format(new Date(item.observedAt ?? item.receivedAt))),
  datasets: [{
    label: `${metricLabels[props.type].label} (${points.value[0]?.unit ?? ''})`,
    data: points.value.map((item) => item.value),
    borderColor: '#0f766e',
    backgroundColor: 'rgba(15, 118, 110, 0.10)',
    pointRadius: points.value.length > 40 ? 0 : 2,
    borderWidth: 2,
    tension: 0.3,
    fill: true,
  }],
}));
const options = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false as const,
  plugins: { legend: { display: false }, tooltip: { intersect: false, mode: 'index' as const } },
  scales: {
    x: { grid: { display: false }, ticks: { maxTicksLimit: 6 } },
    y: { grid: { color: '#e8efed' }, ticks: { maxTicksLimit: 5 } },
  },
};
</script>

<template>
  <div class="h-64 min-w-0">
    <Line v-if="points.length" :data="chartData" :options="options" />
    <div v-else class="grid h-full place-items-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-400">Aucune donnée pour cette période</div>
  </div>
</template>
