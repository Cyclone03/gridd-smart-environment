<script setup lang="ts">
import LocationTreeNode from '@/components/locations/LocationTreeNode.vue';
import { useLocationsStore } from '@/stores/locations.store';
const store = useLocationsStore();
</script>

<template>
  <section class="space-y-5">
    <div><p class="section-kicker">Structure spatiale</p><h2 class="mt-1 text-2xl font-semibold">Localisations et capteurs</h2><p class="mt-1 text-sm text-slate-500">Hiérarchie reconstruite à partir des métadonnées des observations.</p></div>
    <div class="panel p-5 md:p-7">
      <ul v-if="store.hierarchy.length" class="space-y-3"><LocationTreeNode v-for="node in store.hierarchy" :key="`${node.kind}-${node.id}`" :node="node" /></ul>
      <div v-else class="py-16 text-center text-slate-500"><i class="pi pi-sitemap mb-3 text-4xl text-slate-300" /><p class="font-medium">Aucune localisation disponible</p><p class="mt-1 text-sm">La hiérarchie apparaîtra après réception d’observations complètes.</p></div>
    </div>
  </section>
</template>
