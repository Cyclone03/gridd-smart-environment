<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import AppShell from '@/components/layout/AppShell.vue';
import { useDashboardStore } from '@/stores/dashboard.store';

const dashboard = useDashboardStore();
onMounted(() => void dashboard.initialize());
onUnmounted(() => dashboard.stopRealtime());
</script>

<template>
  <AppShell />
</template>
