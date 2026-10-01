<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { useDashboardStore } from '@/stores/dashboard.store';

const route = useRoute();
const dashboard = useDashboardStore();
const title = computed(() => String(route.meta.title ?? 'GRIDD'));
const links = [
  { to: '/dashboard', label: 'Dashboard', icon: 'pi pi-th-large' },
  { to: '/observations', label: 'Observations', icon: 'pi pi-chart-line' },
  { to: '/alerts', label: 'Alertes', icon: 'pi pi-bell' },
  { to: '/locations', label: 'Localisations', icon: 'pi pi-sitemap' },
];
</script>

<template>
  <div class="min-h-screen bg-canvas text-ink lg:grid lg:grid-cols-[248px_1fr]">
    <aside class="hidden border-r border-slate-200 bg-[#102b29] px-5 py-7 text-white lg:flex lg:flex-col">
      <div class="mb-10 flex items-center gap-3 px-2">
        <div class="grid h-10 w-10 place-items-center rounded-xl bg-brand-500 font-bold">G</div>
        <div><p class="font-semibold">GRIDD</p><p class="text-xs text-teal-100/70">Smart Environment</p></div>
      </div>
      <nav class="space-y-2" aria-label="Navigation principale">
        <RouterLink v-for="link in links" :key="link.to" :to="link.to" class="nav-link">
          <i :class="link.icon" aria-hidden="true" /><span>{{ link.label }}</span>
        </RouterLink>
      </nav>
      <div class="mt-auto rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-teal-50/75">
        <p class="mb-1 font-semibold text-white">MGL869</p>
        <p>Environnement intelligent · GRIDD</p>
      </div>
    </aside>

    <div class="min-w-0 pb-20 lg:pb-0">
      <header class="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur md:px-8">
        <div><p class="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">GRIDD · ETS</p><h1 class="text-lg font-semibold">{{ title }}</h1></div>
        <div class="flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold" :class="dashboard.realtimeConnected ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-700'">
          <span class="h-2 w-2 rounded-full" :class="dashboard.realtimeConnected ? 'bg-emerald-500' : 'bg-amber-500'" />
          {{ dashboard.realtimeConnected ? 'Temps réel connecté' : 'Reconnexion…' }}
        </div>
      </header>
      <main class="mx-auto max-w-[1600px] p-4 md:p-8"><RouterView /></main>
    </div>

    <nav class="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-slate-200 bg-white px-1 py-2 shadow-lg lg:hidden" aria-label="Navigation mobile">
      <RouterLink v-for="link in links" :key="link.to" :to="link.to" class="mobile-nav-link">
        <i :class="link.icon" aria-hidden="true" /><span>{{ link.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>
