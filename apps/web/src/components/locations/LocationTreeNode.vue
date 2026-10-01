<script setup lang="ts">
import type { LocationNode } from '@/stores/locations.store';
defineProps<{ node: LocationNode; depth?: number }>();
const icons: Record<LocationNode['kind'], string> = { site: 'pi pi-map', building: 'pi pi-building', storey: 'pi pi-clone', space: 'pi pi-box', zone: 'pi pi-map-marker', sensor: 'pi pi-wifi' };
</script>

<template>
  <li>
    <div class="flex items-center gap-3 rounded-xl border border-slate-100 bg-white px-4 py-3" :style="{ marginLeft: `${(depth ?? 0) * 12}px` }">
      <span class="grid h-8 w-8 place-items-center rounded-lg bg-brand-50 text-brand-700"><i :class="icons[node.kind]" /></span>
      <div><p class="text-sm font-semibold text-slate-800">{{ node.label }}</p><p class="text-xs capitalize text-slate-400">{{ node.kind }} · {{ node.id }}</p></div>
    </div>
    <ul v-if="node.children.length" class="mt-2 space-y-2 border-l border-slate-200 pl-2">
      <LocationTreeNode v-for="child in node.children" :key="`${child.kind}-${child.id}`" :node="child" :depth="(depth ?? 0) + 1" />
    </ul>
  </li>
</template>
